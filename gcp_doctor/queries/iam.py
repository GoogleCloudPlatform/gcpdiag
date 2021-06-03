# Lint as: python3
"""Queries related to GCP Kubernetes Engine clusters."""

import logging
from typing import Any, Dict, List, Mapping

from gcp_doctor import cache, config
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


@cache.cached_api_call(expire=config.STATIC_DOCUMENTS_EXPIRY_SECONDS)
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
    """Return permisions for an member (either a user or serviceAccount).

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


@cache.cached_api_call(in_memory=True)
def get_project_policy(project_id):
  """Return the ProjectPolicy object for a project, caching the result."""
  return ProjectPolicy(project_id)
