# Lint as: python3
"""Queries related to GCP Kubernetes Engine clusters."""

import logging
import re
from typing import Any, Dict, List, Mapping

import googleapiclient.errors

from gcp_doctor import caching, config, models, utils
from gcp_doctor.queries import apis

_predefined_roles: Dict[str, Any] = {}
_predefined_roles_initialized: bool = False


def _get_predefined_roles() -> Mapping[str, Any]:
  """Get the list of predefined roles and keep it in memory."""
  global _predefined_roles
  global _predefined_roles_initialized
  if not _predefined_roles_initialized:
    _predefined_roles = _fetch_predefined_roles()
    _predefined_roles_initialized = True
  return _predefined_roles


@caching.cached_api_call(expire=config.STATIC_DOCUMENTS_EXPIRY_SECONDS)
def _fetch_predefined_roles() -> Mapping[str, Any]:
  logging.info('fetching IAM roles: predefined')
  iam_api = apis.get_api('iam', 'v1')
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
def _fetch_roles(parent: str) -> Mapping[str, Any]:
  roles: Dict[str, Any] = {}
  logging.info('fetching IAM roles: %s', parent)
  iam_api = apis.get_api('iam', 'v1')
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
  crm_api = apis.get_api('cloudresourcemanager', 'v1')
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
    predefined_roles = _fetch_predefined_roles()
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
    return True

  def __init__(self, project_id):
    self._project_id = project_id
    self._custom_roles = _fetch_roles('projects/' + self._project_id)
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


@caching.cached_api_call(in_memory=True)
def get_service_accounts(
    context: models.Context) -> Mapping[str, ServiceAccount]:
  """Get a list of Service Accounts matching the given context, key is e-mail.

  https://cloud.google.com/iam/docs/reference/rest/v1/projects.serviceAccounts/list
  """
  accounts: Dict[str, ServiceAccount] = {}
  iam_api = apis.get_api('iam', 'v1')
  for project_id in context.projects:
    logging.info('fetching list of Service Accounts in project %s', project_id)
    request = iam_api.projects().serviceAccounts().list(
        name=f'projects/{project_id}')
    try:
      while request:
        resp = request.execute(num_retries=config.API_RETRIES)
        if 'accounts' not in resp:
          return accounts
        for resp_sa in resp['accounts']:
          # verify that we some minimal data that we expect
          if 'name' not in resp_sa or 'email' not in resp_sa:
            raise RuntimeError(
                'missing data in projects.serviceAccounts.list response')
          sa = ServiceAccount(project_id=project_id, resource_data=resp_sa)
          accounts[resp_sa['email']] = sa
          logging.debug('found service account %s: %s in project %s',
                        resp_sa['name'], sa, project_id)
          request = iam_api.projects().serviceAccounts().list_next(
              previous_request=request, previous_response=resp)
    except googleapiclient.errors.HttpError as err:
      errstr = utils.http_error_message(err)
      # TODO(dwes): implement proper exception classes
      raise ValueError(
          f'can\'t list service accounts for project {project_id}: {errstr}'
      ) from err
  return accounts
