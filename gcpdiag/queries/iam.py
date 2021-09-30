# Copyright 2021 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# Lint as: python3
"""Queries related to GCP Kubernetes Engine clusters."""

import logging
import re
from typing import Any, Dict, List, Mapping

from gcpdiag import caching, config, models, utils
from gcpdiag.queries import apis

_predefined_roles: Dict[str, Any] = {}
_predefined_roles_initialized: bool = False


@caching.cached_api_call(expire=config.STATIC_DOCUMENTS_EXPIRY_SECONDS)
def _fetch_predefined_roles(api_project_id=None) -> Mapping[str, Any]:
  logging.info('fetching IAM roles: predefined')
  iam_api = apis.get_api('iam', 'v1', project_id=api_project_id)
  roles_api = iam_api.roles()
  request = roles_api.list(parent='', view='FULL')
  roles: Dict[str, Any] = {}
  while True:
    response = request.execute(num_retries=config.API_RETRIES)
    for role in response.get('roles', []):
      name = str(role['name'])
      roles[name] = role
    request = roles_api.list_next(previous_request=request,
                                  previous_response=response)
    if request is None:
      break
  return roles


# Note: caching is done with get_project_policy
def _fetch_roles(parent: str, api_project_id) -> Mapping[str, Any]:
  roles: Dict[str, Any] = {}
  logging.info('fetching IAM roles: %s', parent)
  iam_api = apis.get_api('iam', 'v1', api_project_id)
  roles_api = iam_api.projects().roles()
  request = roles_api.list(parent=parent, view='FULL')
  while True:
    response = request.execute(num_retries=config.API_RETRIES)
    for role in response.get('roles', []):
      name = str(role['name'])
      roles[name] = role
    request = roles_api.list_next(previous_request=request,
                                  previous_response=response)
    if request is None:
      break
  return roles


# Note: caching is done with get_project_policy
def _fetch_policy(project_id: str):
  logging.info('fetching IAM policy of project %s', project_id)
  crm_api = apis.get_api('cloudresourcemanager', 'v1', project_id)
  request = crm_api.projects().getIamPolicy(resource=project_id)
  response = request.execute()
  policy: Dict[str, Any] = {
      'by_member': {},
  }
  if not 'bindings' in response:
    return
  for binding in response['bindings']:
    if not 'role' in binding or not 'members' in binding:
      continue
    for member in binding['members']:
      policy['by_member'].setdefault(member, {'roles': {}})
      policy['by_member'][member]['roles'][binding['role']] = 1

  # Pre-fetch service accounts using a single batch request.
  # Note: not implemented as a generator expression because
  # it looks ugly without assignment expressions, available
  # only with Python >= 3.8.
  sa_emails = []
  for member in policy['by_member']:
    # Note: not matching / makes sure that we don't match for example fleet
    # workload identities:
    # https://cloud.google.com/anthos/multicluster-management/fleets/workload-identity
    m = re.match(r'serviceAccount:([^/]+)$', member)
    if m:
      sa_emails.append(m.group(1))
  _batch_fetch_service_accounts(sa_emails, project_id)

  return policy


class ProjectPolicy:
  """Represents the IAM policy of a single project.

  Note that you should use the get_project_policy() method so that the
  objects are cached and you don't re-fetch the project policy.

  See also the API documentation:
  https://cloud.google.com/resource-manager/reference/rest/v1/projects/getIamPolicy
  """
  _project_id: str
  _policy: Dict[str, Any]
  _custom_roles: Mapping[str, Mapping[str, Any]]

  def _get_role_permissions(self, role: str) -> List[str]:
    if role in self._custom_roles:
      return self._custom_roles[role].get('includedPermissions', [])
    predefined_roles = _fetch_predefined_roles(api_project_id=self._project_id)
    if role in predefined_roles:
      permissions: List[str] = predefined_roles[role].get(
          'includedPermissions', [])
      return permissions
    raise ValueError('unknown role: ' + role)

  def _init_member_permissions(self, member):
    if not member.startswith('user:') and not member.startswith(
        'serviceAccount:'):
      raise ValueError('member must start with user: or serviceAccount:')

    if member not in self._policy['by_member']:
      return
    member_policy = self._policy['by_member'][member]
    if 'permissions' not in member_policy and 'roles' in member_policy:
      # lazy-initialize exploded roles in 'permissions'
      permissions_dict = {}
      for role in member_policy['roles']:
        for p in self._get_role_permissions(role):
          permissions_dict[p] = 1
      member_policy['permissions'] = permissions_dict

  def get_member_permissions(self, member: str) -> List[str]:
    """Return permissions for an member (either a user or serviceAccount).

    The "member" can be a user or a service account and must be specified with
    the IAM member syntax, i.e. using the prefixes `user:` or `serviceAccount:`.
    """

    self._init_member_permissions(member)
    try:
      return sorted(self._policy['by_member'][member]['permissions'].keys())
    except KeyError:
      return []

  def has_permission(self, member: str, permission: str) -> bool:
    """Return true if user or service account member has this project-level permission.

    Note that the member must be prefixed with `user:` or `serviceAccount:`,
    depending on what type of member it is.
    """

    self._init_member_permissions(member)
    try:
      return self._policy['by_member'][member]['permissions'][permission]
    except KeyError:
      return False

  def has_role_permissions(self, member: str, role: str) -> bool:
    """Check whether this member has all the permissions defined by this role."""

    for p in self._get_role_permissions(role):
      # exceptions: some permissions can only be set at org level or aren't
      # supported in custom roles
      if p.startswith('resourcemanager.projects.') or p.startswith(
          'stackdriver.projects.'):
        continue
      if not self.has_permission(member, p):
        logging.debug('%s doesn\'t have permission %s', member, p)
        return False

    # If this is a service account, make sure that the service account is enabled.
    m = re.match(r'serviceAccount:([^/]+)$', member)
    if m:
      if not is_service_account_enabled(m.group(1), self._project_id):
        logging.info('service account %s has role %s, but is disabled!',
                     m.group(1), role)
        return False

    return True

  def __init__(self, project_id):
    self._project_id = project_id
    self._custom_roles = _fetch_roles('projects/' + self._project_id,
                                      api_project_id=self._project_id)
    self._policy = _fetch_policy(project_id)


@caching.cached_api_call(in_memory=True)
def get_project_policy(project_id):
  """Return the ProjectPolicy object for a project, caching the result."""
  return ProjectPolicy(project_id)


class ServiceAccount(models.Resource):
  """ Class represents the service account.

  Add more fields as needed from the declaration:
  https://cloud.google.com/iam/docs/reference/rest/v1/projects.serviceAccounts#ServiceAccount
  """
  _resource_data: dict

  def __init__(self, project_id, resource_data):
    super().__init__(project_id=project_id)
    self._resource_data = resource_data

  @property
  def name(self) -> str:
    return self._resource_data['name']

  @property
  def email(self) -> str:
    return self._resource_data['email']

  @property
  def disabled(self) -> bool:
    return self._resource_data.get('disabled', False)

  @property
  def full_path(self) -> str:
    # example: "name":
    # "projects/skanzhelev-gke-dev/serviceAccounts/test-service-account-1
    #                               @skanzhelev-gke-dev.iam.gserviceaccount.com"
    return self.name

  @property
  def short_path(self) -> str:
    path = self.full_path
    path = re.sub(r'^projects/', '', path)
    path = re.sub(r'/serviceAccounts/', '/', path)
    return path


SERVICE_AGENT_DOMAINS = (
    # https://cloud.google.com/iam/docs/service-accounts
    'cloudservices.gserviceaccount.com',

    # https://cloud.google.com/iam/docs/service-agents
    'cloudbuild.gserviceaccount.com',
    'cloudcomposer-accounts.iam.gserviceaccount.com',
    'cloud-filer.iam.gserviceaccount.com',
    'cloud-memcache-sa.iam.gserviceaccount.com',
    'cloud-ml.google.com.iam.gserviceaccount.com',
    'cloud-redis.iam.gserviceaccount.com',
    'cloud-tpu.iam.gserviceaccount.com',
    'compute-system.iam.gserviceaccount.com',
    'container-analysis.iam.gserviceaccount.com',
    'container-engine-robot.iam.gserviceaccount.com',
    'containerregistry.iam.gserviceaccount.com',
    'dataflow-service-producer-prod.iam.gserviceaccount.com',
    'dataproc-accounts.iam.gserviceaccount.com',
    'dlp-api.iam.gserviceaccount.com',
    'endpoints-portal.iam.gserviceaccount.com',
    'firebase-rules.iam.gserviceaccount.com',
    'gae-api-prod.google.com.iam.gserviceaccount.com',
    'gcf-admin-robot.iam.gserviceaccount.com',
    'gcp-gae-service.iam.gserviceaccount.com',
    'gcp-sa-aiplatform-cc.iam.gserviceaccount.com',
    'gcp-sa-aiplatform.iam.gserviceaccount.com',
    'gcp-sa-anthosaudit.iam.gserviceaccount.com',
    'gcp-sa-anthosconfigmanagement.iam.gserviceaccount.com',
    'gcp-sa-anthos.iam.gserviceaccount.com',
    'gcp-sa-anthosidentityservice.iam.gserviceaccount.com',
    'gcp-sa-anthossupport.iam.gserviceaccount.com',
    'gcp-sa-apigateway.iam.gserviceaccount.com',
    'gcp-sa-apigateway-mgmt.iam.gserviceaccount.com',
    'gcp-sa-apigee.iam.gserviceaccount.com',
    'gcp-sa-appdevexperience.iam.gserviceaccount.com',
    'gcp-sa-artifactregistry.iam.gserviceaccount.com',
    'gcp-sa-assuredworkloads.iam.gserviceaccount.com',
    'gcp-sa-automl.iam.gserviceaccount.com',
    'gcp-sa-bigqueryconnection.iam.gserviceaccount.com',
    'gcp-sa-bigquerydatatransfer.iam.gserviceaccount.com',
    'gcp-sa-bigtable.iam.gserviceaccount.com',
    'gcp-sa-binaryauthorization.iam.gserviceaccount.com',
    'gcp-sa-cloudasset.iam.gserviceaccount.com',
    'gcp-sa-cloudbuild.iam.gserviceaccount.com',
    'gcp-sa-cloud-ids.iam.gserviceaccount.com',
    'gcp-sa-cloudiot.iam.gserviceaccount.com',
    'gcp-sa-cloudkms.iam.gserviceaccount.com',
    'gcp-sa-cloudscheduler.iam.gserviceaccount.com',
    'gcp-sa-cloud-sql.iam.gserviceaccount.com',
    'gcp-sa-cloudtasks.iam.gserviceaccount.com',
    'gcp-sa-cloud-trace.iam.gserviceaccount.com',
    'gcp-sa-contactcenterinsights.iam.gserviceaccount.com',
    'gcp-sa-containerscanning.iam.gserviceaccount.com',
    'gcp-sa-datafusion.iam.gserviceaccount.com',
    'gcp-sa-datalabeling.iam.gserviceaccount.com',
    'gcp-sa-datamigration.iam.gserviceaccount.com',
    'gcp-sa-datapipelines.iam.gserviceaccount.com',
    'gcp-sa-datastream.iam.gserviceaccount.com',
    'gcp-sa-datastudio.iam.gserviceaccount.com',
    'gcp-sa-dialogflow.iam.gserviceaccount.com',
    'gcp-sa-ekms.iam.gserviceaccount.com',
    'gcp-sa-endpoints.iam.gserviceaccount.com',
    'gcp-sa-eventarc.iam.gserviceaccount.com',
    'gcp-sa-firebasemods.iam.gserviceaccount.com',
    'gcp-sa-firebasestorage.iam.gserviceaccount.com',
    'gcp-sa-firestore.iam.gserviceaccount.com',
    'gcp-sa-firewallinsights.iam.gserviceaccount.com',
    'gcp-sa-gameservices.iam.gserviceaccount.com',
    'gcp-sa-gkehub.iam.gserviceaccount.com',
    'gcp-sa-gsuiteaddons.iam.gserviceaccount.com',
    'gcp-sa-healthcare.iam.gserviceaccount.com',
    'gcp-sa-krmapihosting-dataplane.iam.gserviceaccount.com',
    'gcp-sa-krmapihosting.iam.gserviceaccount.com',
    'gcp-sa-ktd-control.iam.gserviceaccount.com',
    'gcp-sa-lifesciences.iam.gserviceaccount.com',
    'gcp-sa-logging.iam.gserviceaccount.com',
    'gcp-sa-mcmetering.iam.gserviceaccount.com',
    'gcp-sa-mcsd.iam.gserviceaccount.com',
    'gcp-sa-meshconfig.iam.gserviceaccount.com',
    'gcp-sa-meshcontrolplane.iam.gserviceaccount.com',
    'gcp-sa-meshdataplane.iam.gserviceaccount.com',
    'gcp-sa-metastore.iam.gserviceaccount.com',
    'gcp-sa-mi.iam.gserviceaccount.com',
    'gcp-sa-monitoring.iam.gserviceaccount.com',
    'gcp-sa-monitoring-notification.iam.gserviceaccount.com',
    'gcp-sa-multiclusteringress.iam.gserviceaccount.com',
    'gcp-sa-networkconnectivity.iam.gserviceaccount.com',
    'gcp-sa-networkmanagement.iam.gserviceaccount.com',
    'gcp-sa-notebooks.iam.gserviceaccount.com',
    'gcp-sa-ondemandscanning.iam.gserviceaccount.com',
    'gcp-sa-osconfig.iam.gserviceaccount.com',
    'gcp-sa-privateca.iam.gserviceaccount.com',
    'gcp-sa-prod-bigqueryomni.iam.gserviceaccount.com',
    'gcp-sa-prod-dai-core.iam.gserviceaccount.com',
    'gcp-sa-pubsub.iam.gserviceaccount.com',
    'gcp-sa-rbe.iam.gserviceaccount.com',
    'gcp-sa-recommendationengine.iam.gserviceaccount.com',
    'gcp-sa-retail.iam.gserviceaccount.com',
    'gcp-sa-scc-notification.iam.gserviceaccount.com',
    'gcp-sa-scc-vmtd.iam.gserviceaccount.com',
    'gcp-sa-secretmanager.iam.gserviceaccount.com',
    'gcp-sa-servicedirectory.iam.gserviceaccount.com',
    'gcp-sa-servicemesh.iam.gserviceaccount.com',
    'gcp-sa-slz.iam.gserviceaccount.com',
    'gcp-sa-spanner.iam.gserviceaccount.com',
    'gcp-sa-tpu.iam.gserviceaccount.com',
    'gcp-sa-transcoder.iam.gserviceaccount.com',
    'gcp-sa-translation.iam.gserviceaccount.com',
    'gcp-sa-vmmigration.iam.gserviceaccount.com',
    'gcp-sa-vmwareengine.iam.gserviceaccount.com',
    'gcp-sa-vpcaccess.iam.gserviceaccount.com',
    'gcp-sa-websecurityscanner.iam.gserviceaccount.com',
    'gcp-sa-workflows.iam.gserviceaccount.com',
    'genomics-api.google.com.iam.gserviceaccount.com',
    'remotebuildexecution.iam.gserviceaccount.com',
    'serverless-robot-prod.iam.gserviceaccount.com',
    'service-consumer-management.iam.gserviceaccount.com',
    'service-networking.iam.gserviceaccount.com',
    'sourcerepo-service-accounts.iam.gserviceaccount.com',

    # https://firebase.google.com/support/guides/service-accounts
    'appspot.gserviceaccount.com',
    'cloudservices.gserviceaccount.com',
    'crashlytics-bigquery-prod.iam.gserviceaccount.com',
    'fcm-bq-export-prod.iam.gserviceaccount.com',
    'firebase-sa-management.iam.gserviceaccount.com',
    'performance-bq-export-prod.iam.gserviceaccount.com',
    'predictions-bq-export-prod.iam.gserviceaccount.com',
    'system.gserviceaccount.com',

    # additional
    'gcp-sa-computescanning.iam.gserviceaccount.com',
)

# The main reason to have two dicts instead of using for example None as value,
# is that it works better for static typing (i.e. avoiding Optional[]).
_service_account_cache: Dict[str, ServiceAccount] = {}
_service_account_cache_fetched: Dict[str, bool] = {}
_service_account_cache_is_not_found: Dict[str, bool] = {}


def _batch_fetch_service_accounts(emails: List[str], billing_project_id: str):
  """Retrieve a list of service accounts.

  This function is used when inspecting a project_id, to retrieve all service accounts
  that are used in the IAM policy, so that we can do this in a single batch request.
  The goal is to be able to call is_service_account_enabled() without triggering
  another API call.
  """

  global _service_account_cache
  iam_api = apis.get_api('iam', 'v1', billing_project_id)
  service_accounts_api = iam_api.projects().serviceAccounts()

  def callback(request_id, response, exception):
    if exception:
      gcp_exception = utils.GcpApiError(exception)
      # 403 or 404 is expected for Google-managed service agents.
      if request_id.partition('@')[2] in SERVICE_AGENT_DOMAINS:
        # Too noisy even for debug-level
        # logging.debug(
        #     'ignoring error retrieving google-managed service agent %s: %s',
        #     request_id, gcp_exception)
        pass
      elif gcp_exception.status == 404:
        _service_account_cache_is_not_found[request_id] = True
      else:
        logging.warning("can't get service account %s: %s", request_id,
                        gcp_exception)
      return

    sa = ServiceAccount(response['projectId'], response)
    _service_account_cache[sa.email] = sa

  emails_to_fetch = [
      e for e in emails if e not in _service_account_cache_fetched
  ]
  while emails_to_fetch:
    batch = iam_api.new_batch_http_request(callback=callback)
    for _ in range(1000):
      try:
        email = emails_to_fetch.pop(0)
        batch.add(request=service_accounts_api.get(
            name='projects/-/serviceAccounts/' + email),
                  request_id=email)
        _service_account_cache_fetched[email] = True
      except IndexError:
        break
    batch.execute()


def is_service_account_existing(email: str, billing_project_id: str) -> bool:
  """Verify that a service account exists.

  If we get a non-404 API error when retrieving the service account, we will assume
  that the service account exists, not to throw false positives (but
  a warning will be printed out).
  """
  # Make sure that the service account is fetched (this is also
  # called by get_project_policy).
  _batch_fetch_service_accounts([email], billing_project_id)
  return email not in _service_account_cache_is_not_found


def is_service_account_enabled(email: str, billing_project_id: str) -> bool:
  """Verify that a service account exists and is enabled.

  If we get an API error when retrieving the service account, we will assume
  that the service account is enabled, not to throw false positives (but
  a warning will be printed out).
  """
  _batch_fetch_service_accounts([email], billing_project_id)
  return (email not in _service_account_cache_is_not_found) and \
      not (email in _service_account_cache and _service_account_cache[email].disabled)
