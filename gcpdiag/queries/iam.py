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

import abc
import collections
import functools
import logging
import re
from typing import Any, Dict, List, Optional, Tuple, Type

import googleapiclient
import googleapiclient.errors

from gcpdiag import caching, config, models, utils
from gcpdiag.queries import apis, apis_utils, crm


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
    # roles should usually include one or more permissions
    return self._resource_data.get('includedPermissions', [])


class RoleNotFoundError(Exception):
  pass


# Note: caching is done in get_*_roles because of different caching policies
def _fetch_iam_roles(parent: str, api_project_id: str) -> Dict[str, Role]:

  def _make_role(resource_data: Dict[str, Any]) -> Tuple[str, Role]:
    resource_name = resource_data['name']
    return resource_name, Role(resource_data)

  logging.info("fetching IAM roles of '%s'", parent)
  iam_api = apis.get_api('iam', 'v1', api_project_id)
  if parent.startswith('projects/'):
    roles_api = iam_api.projects().roles()
  elif parent.startswith('organizations/'):
    roles_api = iam_api.organizations().roles()
  else:
    roles_api = iam_api.roles()
  try:
    res = apis_utils.list_all(roles_api.list(view='FULL', parent=parent),
                              roles_api.list_next, 'roles')
  except googleapiclient.errors.HttpError as err:
    logging.error('failed to list roles: %s', err)
    raise utils.GcpApiError(err) from err

  return dict(map(_make_role, res))


# Cache both in memory and on disk, so that multiple calls during the same
# gcpdiag execution are very quick, but also results are cached on disk
# for the next execution. Only caching on disk causes slowness because this method
# is called multiple times.
@functools.lru_cache()
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
  logging.info("fetching IAM role '%s'", name)
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


class BaseIAMPolicy(models.Resource):
  """Common class for IAM policies"""

  _name: str
  _policy_by_member: Dict[str, Any]

  @property
  def full_path(self):
    return self._name

  @abc.abstractmethod
  def _is_resource_permission(self, permission: str) -> bool:
    """Checks that a permission is applicable to the resource

    Any role can be assigned on a resource level but only a subset of
    permissions will be relevant to a resource
    Irrelevant permissions are ignored in `has_role_permissions` method
    """
    pass

  def _expand_policy(self, resource_data: Dict[str, Any]) -> Dict[str, Any]:
    """Groups `getIamPolicy` bindings by member

    API response contains a list of bindings of a role to members:
    {
      "bindings": [
      {
        "role": "roles/resourcemanager.organizationAdmin",
        "members": [
          "user:mike@example.com",
          "serviceAccount:my-project-id@appspot.gserviceaccount.com"
        ]
      },
      ...
    }

    This method will convert those bindings into the following structure:
    {
      "user:mike@example.com": {
        "roles": { "roles/resourcemanager.organizationAdmin" },
      },
      "serviceAccount:my-project-id@appspot.gserviceaccount.com": {
        "roles": { "roles/resourcemanager.organizationAdmin" },
      },
    }
    """

    policy_roles = set()
    policy_by_member: Dict[str, Any] = collections.defaultdict(dict)

    # Empty lists are omitted in GCP API responses
    for binding in resource_data.get('bindings', []):
      if 'condition' in binding:
        logging.warning(
            'IAM binding contains a condition, which would be ignored: %s',
            binding,
        )

      # IAM binding should always have a role and at least one member
      policy_roles.add(binding['role'])
      for member in binding['members']:
        member_policy = policy_by_member[member]
        member_policy.setdefault('roles', set()).add(binding['role'])

    # Populate cache for IAM roles used in the policy
    # Unlike `has_role_permissions` this part will be executed inside
    # `prefetch_rule` and will benefit from multi-threading execution
    for role in policy_roles:
      # Ignore all errors - there could be no rules involving this role
      try:
        _get_iam_role(role, self.project_id)
      except (RoleNotFoundError, utils.GcpApiError) as err:
        # Ignore roles if cannot retrieve a role
        # For example, due to lack of permissions
        if isinstance(err, utils.GcpApiError):
          logging.error('API failure getting IAM roles: %s', err)
          raise utils.GcpApiError(err) from err
        elif isinstance(err, RoleNotFoundError):
          logging.warning("Unable to get IAM role '%s', ignoring: %s", role,
                          err)

    # Populate cache for service accounts used in the policy
    # Note: not implemented as a generator expression because
    # it looks ugly without assignment expressions, available
    # only with Python >= 3.8.
    sa_emails = set()
    for member in policy_by_member.keys():
      # Note: not matching / makes sure that we don't match for example fleet
      # workload identities:
      # https://cloud.google.com/anthos/multicluster-management/fleets/workload-identity
      m = re.match(r'serviceAccount:([^/]+)$', member)
      if m:
        sa_emails.add(m.group(1))
    _batch_fetch_service_accounts(list(sa_emails), self.project_id)

    return policy_by_member

  def _expand_member_policy(self, member: str):
    """Expands member roles into set of permissions

    Permissions are using "lazy" initialization and only expanded if needed
    """
    member_policy = self._policy_by_member.get(member)
    if not member_policy or 'permissions' in member_policy:
      return

    permissions = set()
    for role in member_policy['roles']:
      try:
        permissions.update(_get_iam_role(role, self.project_id).permissions)
      except (RoleNotFoundError, utils.GcpApiError) as err:
        if isinstance(err, utils.GcpApiError):
          logging.error('API failure getting IAM roles: %s', err)
          raise utils.GcpApiError(err) from err
        elif isinstance(err, RoleNotFoundError):
          logging.warning("Unable to find IAM role '%s', ignoring: %s", role,
                          err)
    member_policy['permissions'] = permissions

  def _is_active_member(self, member: str) -> bool:
    """Checks that the member isn't disabled

    Currently supports only service accounts and not other account types
    Used in `has_role_permissions` and similar methods to ensure that
    the member isn't disabled and permissions are effectively working
    """

    # If this is a service account, make sure that the service account is enabled.
    # Note: not matching / makes sure that we don't match for example fleet
    # workload identities:
    # https://cloud.google.com/anthos/multicluster-management/fleets/workload-identity
    m = re.match(r'serviceAccount:([^/]+)$', member)
    if m:
      if not is_service_account_enabled(m.group(1), self.project_id):
        logging.info('service account %s is disabled', m.group(1))
        return False

    return True

  def __init__(self, project_id: Optional[str], name: str,
               resource_data: Dict[str, Any]):
    super().__init__(project_id)
    self._name = name
    self._policy_by_member = self._expand_policy(resource_data)

  def get_member_permissions(self, member: str) -> List[str]:
    """Return permissions for a member (either a user or serviceAccount).

    The "member" can be a user or a service account and must be specified with
    the IAM member syntax, i.e. using the prefixes `user:` or `serviceAccount:`.
    """

    if member not in self._policy_by_member:
      return []

    self._expand_member_policy(member)
    return sorted(self._policy_by_member[member]['permissions'])

  def get_members(self) -> List[str]:
    """Returns the IAM members of the project.

    The "member" can be a user or a service account and is specified with
    the IAM member syntax, i.e. using the prefixes `user:` or `serviceAccount:`.
    """
    return list(self._policy_by_member.keys())

  def get_member_type(self, member) -> Optional[str]:
    """Returns the IAM members of the project.

    The "member" can be a user or a service account and is specified with
    the IAM member syntax, i.e. using the prefixes `user:` or `serviceAccount:`.
    """
    for m in self._policy_by_member.keys():
      parts = m.split(':')
      if member == parts[1]:
        return parts[0]
    return None

  def has_permission(self, member: str, permission: str) -> bool:
    """Return true if user or service account member has this permission.

    Note that any indirect bindings, for example through group membership,
    aren't supported and only direct bindings to this member are checked
    """

    if member not in self._policy_by_member:
      return False

    self._expand_member_policy(member)
    if permission not in self._policy_by_member[member]['permissions']:
      return False
    return self._is_active_member(member)

  def has_any_permission(self, member: str, permission: set[str]) -> bool:
    """Return true if user or service account member has any of these permission.

    Note that any indirect bindings, for example through group membership,
    aren't supported and only direct bindings to this member are checked
    """

    if member not in self._policy_by_member:
      return False

    self._expand_member_policy(member)
    if any(
        p in self._policy_by_member[member]['permissions'] for p in permission):
      return True
    return self._is_active_member(member)

  def _has_role(self, member: str, role: str) -> bool:
    """Checks that the member has this role

    It performs exact match and doesn't expand role to list of permissions.
    Note that this method is not public because users of this module should
    use has_role_permissions(), i.e. verify effective permissions instead of
    roles.
    """

    if member not in self._policy_by_member:
      return False

    if role not in self._policy_by_member[member]['roles']:
      return False
    return self._is_active_member(member)

  def has_role_permissions(self, member: str, role: str) -> bool:
    """Checks that this member has all the permissions defined by this role"""

    if member not in self._policy_by_member:
      return False

    # Avoid expanding roles to permissions
    if self._has_role(member, role):
      # member status was already checked in `has_role`
      return True

    self._expand_member_policy(member)
    role_permissions = {
        p for p in _get_iam_role(role, self.project_id).permissions
        if self._is_resource_permission(p)
    }

    missing_roles = (role_permissions -
                     self._policy_by_member[member]['permissions'])
    if missing_roles:
      logging.debug(
          "member '%s' doesn't have permissions %s",
          member,
          ','.join(missing_roles),
      )
      return False
    return self._is_active_member(member)


def fetch_iam_policy(
    request,
    resource_class: Type[BaseIAMPolicy],
    project_id: Optional[str],
    name: str,
    raise_error_if_fails=True,
):
  """Executes `getIamPolicy` request and converts into a resource class

  Supposed to be used by `get_*_policy` functions in gcpdiag.queries.* and
  requires an API request, which can be executed, to be passed in parameters

  An abstract policy request should look like:
    class ResourcePolicy(BaseIAMPolicy):
      pass

    def get_resource_policy(name):
      api_request = get_api(..).resources().get(name=name)
      ...
      return fetch_iam_policy(api_request, ResourcePolicy, project_id, name)

  Note: API calls aren't cached and it should be done externally
  """

  logging.info("fetching IAM policy of '%s'", name)
  try:
    response = request.execute(num_retries=config.API_RETRIES)
  except googleapiclient.errors.HttpError as err:
    if raise_error_if_fails:
      raise utils.GcpApiError(err) from err
    else:
      return
  return resource_class(project_id, name, response)


class ProjectPolicy(BaseIAMPolicy):
  """Represents the IAM policy of a single project.

  Note that you should use the get_project_policy() method so that the
  objects are cached and you don't re-fetch the project policy.

  See also the API documentation:
  https://cloud.google.com/resource-manager/reference/rest/v1/projects/getIamPolicy
  """

  def _is_resource_permission(self, permission: str) -> bool:
    # Filter out permissions that can be granted only on organization or folders
    # It also excludes some permissions that aren't supported in custom roles
    #
    # https://cloud.google.com/resource-manager/docs/access-control-proj#permissions
    # https://cloud.google.com/monitoring/access-control#custom_roles
    if permission.startswith('resourcemanager.projects.'
                            ) or permission.startswith('stackdriver.projects.'):
      return False
    return True


@caching.cached_api_call(in_memory=True)
def get_project_policy(project_id: str,
                       raise_error_if_fails=True) -> ProjectPolicy:
  """Return the ProjectPolicy object for a project, caching the result."""

  resource_name = f'projects/{project_id}'

  crm_api = apis.get_api('cloudresourcemanager', 'v3', project_id)
  request = crm_api.projects().getIamPolicy(resource='projects/' + project_id)

  return fetch_iam_policy(request, ProjectPolicy, project_id, resource_name,
                          raise_error_if_fails)


class OrganizationPolicy(BaseIAMPolicy):
  """Represents the IAM policy of a single organization using v1 API.

  See also the API documentation:
  https://cloud.google.com/resource-manager/reference/rest/v1/organizations/getIamPolicy
  """

  def _is_resource_permission(self, permission: str) -> bool:
    # Filter out permissions that can be granted only on projects or folders
    if permission.startswith(
        'resourcemanager.projects.') or permission.startswith(
            'resourcemanager.folders.'):
      return False
    return True


@caching.cached_api_call(in_memory=True)
def get_organization_policy(organization_id: str,
                            raise_error_if_fails=True) -> OrganizationPolicy:
  """Return the OrganizationPolicy object for an organization, caching the result."""

  resource_name = f'organizations/{organization_id}'

  crm_api = apis.get_api('cloudresourcemanager', 'v1')
  request = crm_api.organizations().getIamPolicy(resource=resource_name)

  return fetch_iam_policy(request, OrganizationPolicy, None, resource_name,
                          raise_error_if_fails)


class ServiceAccount(models.Resource):
  """Class represents the service account.

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
  def unique_id(self) -> str:
    return self._resource_data['uniqueId']

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
    # gcp-sa-*.iam.gserviceaccount.com included with a separate matching condition
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
)

DEFAULT_SERVICE_ACCOUNT_DOMAINS = (
    'appspot.gserviceaccount.com',
    'developer.gserviceaccount.com',
)

# The main reason to have two dicts instead of using for example None as value,
# is that it works better for static typing (i.e. avoiding Optional[]).
_service_account_cache: Dict[str, ServiceAccount] = {}
_service_account_cache_fetched: Dict[str, bool] = {}
_service_account_cache_is_not_found: Dict[str, bool] = {}


def _batch_fetch_service_accounts(emails: List[str], billing_project_id: str):
  """Retrieve a list of service accounts.

  This function is used when inspecting a project, to retrieve all service
  accounts
  that are used in the IAM policy, so that we can do this in a single batch
  request.
  The goal is to be able to call is_service_account_enabled() without triggering
  another API call.

  `project_id` is used primarily as the default billing project. Service
  accounts from other projects in `emails` will be also retrieved.
  """

  iam_api = apis.get_api('iam', 'v1', billing_project_id)
  service_accounts_api = iam_api.projects().serviceAccounts()

  requests = [
      service_accounts_api.get(
          name=f'projects/{_extract_project_id(email)}/serviceAccounts/{email}')
      for email in emails
      if email not in _service_account_cache_fetched
  ]
  for email in emails:
    _service_account_cache_fetched[email] = True

  for request in requests:
    try:
      response = request.execute(num_retries=config.API_RETRIES)
      sa = ServiceAccount(response['projectId'], response)
      _service_account_cache[sa.email] = sa
    except googleapiclient.errors.HttpError as err:
      exception = utils.GcpApiError(err)
      if exception:
        # Extract the requested service account and its associated project ID
        # from the URI. This is especially useful when dealing with scenarios
        #  involving cross-project service accounts within a project.
        m = re.search(r'/projects/([^/]+)/[^/]+/([^?]+@[^?]+)', request.uri)
        if not m:
          logging.warning("BUG: can't determine SA email from request URI: %s",
                          request.uri)
          continue
        sa_project_id = m.group(1)
        email = m.group(2)

        # 403 or 404 is expected for Google-managed service agents.
        if email.partition('@')[2] in SERVICE_AGENT_DOMAINS or email.partition(
            '@')[2].startswith('gcp-sa-'):
          # Too noisy even for debug-level
          # logging.debug(
          #     'ignoring error retrieving google-managed service agent %s: %s', email, exception)
          pass
        elif (isinstance(exception, utils.GcpApiError) and
              exception.status == 404):
          _service_account_cache_is_not_found[email] = True
        else:
          # Determine if the failing service account belongs to a different project.
          # Retrieving service account details may fail due to various conditions.
          if sa_project_id != billing_project_id:
            logging.warning(
                "can't retrieve service account %s belonging to project %s but"
                ' used in project: %s',
                email,
                sa_project_id,
                billing_project_id,
            )
            _service_account_cache_is_not_found[email] = True
            continue

          project_nr = crm.get_project(sa_project_id).number
          if ((sa_project_id == billing_project_id) and
              re.match(rf'{project_nr}-\w+@', email) or
              email.endswith(f'@{billing_project_id}.iam.gserviceaccount.com')):
            # if retrieving service accounts from the project being inspected fails,
            # we need to fail hard because many rules won't work correctly.
            raise utils.GcpApiError(err) from err

          else:
            logging.warning("can't get service account %s: %s", email,
                            exception)


def _extract_project_id(email: str):
  if email in _service_account_cache:
    return _service_account_cache[email].project_id

  if email.endswith('.iam.gserviceaccount.com') and not (
      email.startswith('service-') or
      email.split('@')[1].startswith('gcp-sa-')):
    project_id = re.split(r'[@ .]', email)[1]
    return project_id
    # extract project number from service agents and compute default SA
  elif (email.partition('@')[2] in SERVICE_AGENT_DOMAINS or
        email.partition('@')[2].startswith('gcp-sa-') or
        email.endswith(DEFAULT_SERVICE_ACCOUNT_DOMAINS[1])):
    # AppEngine Default SA is unique
    if email.endswith(DEFAULT_SERVICE_ACCOUNT_DOMAINS[0]):
      return email.partition('@')[0]

    m = re.search(r'[\d]+', email.partition('@')[0])
    if m and (m.group(0) is not None):
      try:
        project_id = crm.get_project(m.group(0)).id
      except utils.GcpApiError:
        # Default to using '-' wildcard to infer the project.
        # - wildcard character is unreliable and should be used as last resort
        # because it can cause response codes to contain misleading error codes
        # such as 403 for deleted service accounts instead of returning 404
        # https://cloud.google.com/iam/docs/reference/rest/v1/projects.serviceAccounts/get
        logging.warning(
            'Using "-" wildcard to infer host project for service account: %s. '
            'Rules which rely on method: projects.serviceAccounts.get to'
            ' determine '
            'disabled vrs deleted status of %s may produce misleading results. '
            'See: https://cloud.google.com/iam/docs/reference/rest/v1/projects.serviceAccounts/get',
            email,
            email,
        )
        return '-'
      else:
        return project_id
  else:
    logging.warning(
        'Using "-" wildcard to infer host project for service account: %s. '
        'Rules which rely on method: projects.serviceAccounts.get to determine '
        'disabled vrs deleted status of %s may produce misleading results. '
        'See: https://cloud.google.com/iam/docs/reference/rest/v1/projects.serviceAccounts/get',
        email,
        email,
    )
    return '-'


def is_service_account_existing(email: str, billing_project_id: str) -> bool:
  """Verify that a service account exists.

  If we get a non-404 API error when retrieving the service account, we will
  assume
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
  return (email not in _service_account_cache_is_not_found
         ) and not (email in _service_account_cache and
                    _service_account_cache[email].disabled)


class ServiceAccountIAMPolicy(BaseIAMPolicy):

  def _is_resource_permission(self, permission):
    return True


@caching.cached_api_call(in_memory=True)
def get_service_account_iam_policy(
    project_id: str, service_account: str) -> ServiceAccountIAMPolicy:
  """Returns an IAM policy for a service account"""

  resource_name = f'projects/{project_id}/serviceAccounts/{service_account}'

  iam_api = apis.get_api('iam', 'v1', project_id)
  request = (iam_api.projects().serviceAccounts().getIamPolicy(
      resource=resource_name))

  return fetch_iam_policy(request, ServiceAccountIAMPolicy, project_id,
                          resource_name)


@caching.cached_api_call(in_memory=True)
def get_service_account_list(project_id: str) -> List[ServiceAccount]:
  """Returns list of service accounts"""

  iam_api = apis.get_api('iam', 'v1', project_id)
  project_name = f'projects/{project_id}'
  request = iam_api.projects().serviceAccounts().list(name=project_name)
  try:
    response = request.execute(num_retries=config.API_RETRIES)
  except googleapiclient.errors.HttpError as err:
    raise utils.GcpApiError(err) from err
  return [
      ServiceAccount(project_id, service_account)
      for service_account in response.get('accounts', [])
  ]
