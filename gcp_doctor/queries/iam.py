# Lint as: python3
"""Queries related to GCP Kubernetes Engine clusters."""

import functools
import logging
from typing import Any, ClassVar, Dict, List, Mapping

from gcp_doctor import cache, config
from gcp_doctor.queries import apis


@functools.lru_cache(maxsize=None)
def _fetch_roles(parent: str) -> Mapping[str, Any]:
  # Try fetching predefined roles from disk cache.
  if parent == '':
    with cache.get_cache() as diskcache:
      cached_roles = diskcache.get('iam_predefined_roles')
      if cached_roles:
        return cached_roles

  roles: Dict[str, Any] = {}
  logging.info('fetching IAM roles: %s', parent or 'predefined')
  iam_api = apis.get_api('iam', 'v1')
  if parent == '':
    roles_api = iam_api.roles()
  else:
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

  # Store predefined roles in disk cache.
  if parent == '':
    with cache.get_cache() as diskcache:
      diskcache.set('iam_predefined_roles',
                    roles,
                    expire=config.STATIC_DOCUMENTS_EXPIRY_SECONDS)

  return roles


class ProjectPolicy:
  """Represents the IAM policy of a single project.

  Note that you should use the get_project_policy() method so that the
  objects are cached and you don't re-fetch the project policy.

  See also the API documentation:
  https://cloud.google.com/resource-manager/reference/rest/v1/projects/getIamPolicy
  """
  _project_id: str
  _policy: Dict[str, Any]
  _policy_initialized: bool = False
  _predefined_roles: ClassVar[Mapping[str, Mapping[str, Any]]]
  _predefined_roles_initialized: ClassVar[bool] = False
  _custom_roles: Mapping[str, Mapping[str, Any]]
  _custom_roles_initialized: bool = False

  def _init_policy(self):
    if not self._policy_initialized:
      logging.info('fetching IAM policy of project %s', self._project_id)
      crm_api = apis.get_api('cloudresourcemanager', 'v1')
      request = crm_api.projects().getIamPolicy(resource=self._project_id)
      response = request.execute()
      self._policy_initialized = True
      self._policy = {
          'by_member': {},
      }
      if not 'bindings' in response:
        return
      for binding in response['bindings']:
        if not 'role' in binding or not 'members' in binding:
          continue
        for member in binding['members']:
          self._policy['by_member'].setdefault(member, {'roles': {}})
          self._policy['by_member'][member]['roles'][binding['role']] = 1

  def _init_roles(self):
    if not ProjectPolicy._predefined_roles_initialized:
      ProjectPolicy._predefined_roles = _fetch_roles('')
      ProjectPolicy._predefined_roles_initialized = True
    if not self._custom_roles_initialized:
      self._custom_roles = _fetch_roles('projects/' + self._project_id)
      self._custom_roles_initialized = True

  def _get_role_permissions(self, role: str) -> List[str]:
    self._init_roles()
    if role in self._custom_roles:
      return self._custom_roles[role].get('includedPermissions', [])
    if role in ProjectPolicy._predefined_roles:
      permissions: List[str] = ProjectPolicy._predefined_roles[role].get(
          'includedPermissions', [])
      return permissions
    raise ValueError('unknown role: ' + role)

  def _init_member_permissions(self, member):
    if not member.startswith('user:') and not member.startswith(
        'serviceAccount:'):
      raise ValueError('member must start with user: or serviceAccount:')

    self._init_policy()
    if member not in self._policy['by_member']:
      return
    member_policy = self._policy['by_member'][member]
    if 'permissions' not in member_policy and 'roles' in member_policy:
      # lazy-initialize exploded roles in 'permissions'
      for role in member_policy['roles']:
        permissions = self._get_role_permissions(role)
        permissions_dict = {k: 1 for k in permissions}
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


@functools.lru_cache(maxsize=None)
def get_project_policy(project_id):
  """Return the ProjectPolicy object for a project, caching the result."""
  return ProjectPolicy(project_id)
