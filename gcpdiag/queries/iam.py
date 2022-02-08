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
"""Queries related to GCP Identity and Access Management."""

import functools
import logging
import re
from typing import Any, Dict, List, Tuple

import googleapiclient

from gcpdiag import caching, config, models, utils
from gcpdiag.queries import apis, apis_utils


class Role(models.Resource):
  """Represents an IAM role"""

  def __init__(self, resource_data):
    try:
      project_id = utils.get_project_by_res_name(resource_data['name'])
    except ValueError:
      project_id = None

    super().__init__(project_id=project_id)
    self._resource_data = resource_data

  @property
  def name(self) -> str:
    return self._resource_data['name']

  @property
  def full_path(self) -> str:
    return self.name

  @property
  def permissions(self) -> List[str]:
    return self._resource_data['includedPermissions']


class RoleNotFoundError(Exception):
  pass


# Note: caching is done in get_*_roles because of different caching policies
def _fetch_iam_roles(parent: str, api_project_id: str) -> Dict[str, Role]:

  def _make_role(resource_data: Dict[str, Any]) -> Tuple[str, Role]:
    resource_name = resource_data['name']
    return resource_name, Role(resource_data)

  logging.info('fetching IAM roles of \'%s\'', parent)
  iam_api = apis.get_api('iam', 'v1', api_project_id)
  if parent.startswith('projects/'):
    roles_api = iam_api.projects().roles()
  elif parent.startswith('organizations/'):
    roles_api = iam_api.organizations().roles()
  else:
    roles_api = iam_api.roles()

  return dict(
      map(
          _make_role,
          apis_utils.list_all(roles_api.list(view='FULL', parent=parent),
                              roles_api.list_next, 'roles')))


@caching.cached_api_call(expire=config.STATIC_DOCUMENTS_EXPIRY_SECONDS)
def _get_predefined_roles(api_project_id: str) -> Dict[str, Role]:
  return _fetch_iam_roles('', api_project_id)


@caching.cached_api_call(expire=config.STATIC_DOCUMENTS_EXPIRY_SECONDS)
def _get_predefined_role(name: str, api_project_id: str) -> Role:
  """Returns a predefined role using roles.get

  It should only be used if role is internal and cannot be retrieved using
  roles.list. For all other roles, _get_predefined_roles should be preferred
  because of caching efficiency
  """
  logging.info('fetching IAM role \'%s\'', name)
  iam_api = apis.get_api('iam', 'v1', api_project_id)
  request = iam_api.roles().get(name=name)

  try:
    response = request.execute(num_retries=config.API_RETRIES)
  except googleapiclient.errors.HttpError as err:
    if err.resp.status == 404:
      raise RoleNotFoundError(f'unknown role: {name}') from err
    raise utils.GcpApiError(err) from err

  return Role(response)


@caching.cached_api_call(in_memory=True)
def _get_organization_roles(organization_name: str,
                            api_project_id: str) -> Dict[str, Role]:
  return _fetch_iam_roles(organization_name, api_project_id)


@caching.cached_api_call(in_memory=True)
def _get_project_roles(project_name: str,
                       api_project_id: str) -> Dict[str, Role]:
  return _fetch_iam_roles(project_name, api_project_id)


@functools.lru_cache()
def _get_iam_role(name: str, default_project_id: str) -> Role:
  m = re.match(r'(.*)(^|/)roles/.*$', name)
  if not m:
    raise ValueError(f'invalid role: {name}')

  parent = m.group(1)
  if parent == '':
    parent_roles = _get_predefined_roles(default_project_id)
    if name in parent_roles:
      return parent_roles[name]

    # IAM roles can be marked as internal and won't be returned by `list`
    # But they are available using `get` method and can be granted or revoked
    # using gcloud CLI, so using it as a fallback
    return _get_predefined_role(name, default_project_id)

  if parent.startswith('projects/'):
    project_id = utils.get_project_by_res_name(parent)
    parent_roles = _get_project_roles(parent, project_id)
  elif parent.startswith('organizations/'):
    parent_roles = _get_organization_roles(parent, default_project_id)
  else:
    raise ValueError(f'invalid role: {name}')

  if name not in parent_roles:
    raise RoleNotFoundError(f'unknown role: {name}')
  return parent_roles[name]


# Note: caching is done with get_project_policy
def _fetch_policy(project_id: str):
  logging.info('fetching IAM policy of project %s', project_id)
  crm_api = apis.get_api('cloudresourcemanager', 'v1', project_id)
  request = crm_api.projects().getIamPolicy(resource=project_id)
  response = request.execute(num_retries=config.API_RETRIES)
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

  def _get_role_permissions(self, role: str) -> List[str]:
    return _get_iam_role(role, self._project_id).permissions

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
        # Ignore unknown roles for the expansion of permissions (some predefined roles
        # are not returned when listing roles).
        try:
          for p in self._get_role_permissions(role):
            permissions_dict[p] = 1
        except RoleNotFoundError:
          pass
      member_policy['permissions'] = permissions_dict

  def get_member_permissions(self, member: str) -> List[str]:
    """Return permissions for a member (either a user or serviceAccount).

    The "member" can be a user or a service account and must be specified with
    the IAM member syntax, i.e. using the prefixes `user:` or `serviceAccount:`.
    """

    self._init_member_permissions(member)
    try:
      return sorted(self._policy['by_member'][member]['permissions'].keys())
    except KeyError:
      return []

  def get_members(self):
    """Returns the IAM members of the project.

    The "member" can be a user or a service account and is specified with
    the IAM member syntax, i.e. using the prefixes `user:` or `serviceAccount:`.
    """

    return self._policy['by_member'].keys()

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
    self._policy = _fetch_policy(project_id)


@caching.cached_api_call(in_memory=True)
def get_project_policy(project_id):
  """Return the ProjectPolicy object for a project, caching the result."""
  try:
    return ProjectPolicy(project_id)
  except googleapiclient.errors.HttpError as err:
    raise utils.GcpApiError(err) from err


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

  iam_api = apis.get_api('iam', 'v1', billing_project_id)
  service_accounts_api = iam_api.projects().serviceAccounts()
  requests = [
      service_accounts_api.get(name='projects/-/serviceAccounts/' + email)
      for email in emails
      if email not in _service_account_cache_fetched
  ]
  for email in emails:
    _service_account_cache_fetched[email] = True

  for (request, response,
       exception) in apis_utils.batch_execute_all(iam_api, requests):
    if exception:
      # extract from uri what the requested email was
      m = re.search(r'/([^/?]+)(?:\?[^/]*)', request.uri)
      if not m:
        logging.warning("BUG: can't determine SA email from request URI: %s",
                        request.uri)
        continue
      email = m.group(1)

      # 403 or 404 is expected for Google-managed service agents.
      if email.partition('@')[2] in SERVICE_AGENT_DOMAINS:
        # Too noisy even for debug-level
        # logging.debug(
        #     'ignoring error retrieving google-managed service agent %s: %s', email, exception)
        pass
      elif isinstance(exception, utils.GcpApiError) and exception.status == 404:
        _service_account_cache_is_not_found[email] = True
      else:
        logging.warning("can't get service account %s: %s", email, exception)
    else:
      sa = ServiceAccount(response['projectId'], response)
      _service_account_cache[sa.email] = sa


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
