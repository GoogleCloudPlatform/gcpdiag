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
"""Queries related to organization policy constraints."""

import logging
from typing import Dict, List

import googleapiclient.errors

from gcpdiag import caching, config, utils
from gcpdiag.queries import apis

RESOURCE_TYPE_PROJECT = 'projects'
RESOURCE_TYPE_ORGANIZATION = 'organizations'


class PolicyConstraint:

  def __init__(self, name, resource_data):
    self.name = name
    self._resource_data = resource_data

  def __str__(self):
    return self.name + ': ' + self._resource_data.__str__()

  pass


class BooleanPolicyConstraint(PolicyConstraint):

  def is_enforced(self) -> bool:
    return self._resource_data.get('enforced', False)


class ListPolicyConstraint(PolicyConstraint):

  def allowed_values(self) -> List[str]:
    return self._resource_data.get('allowedValues', [])

  def denied_values(self) -> List[str]:
    return self._resource_data.get('deniedValues', [])


class RestoreDefaultPolicyConstraint(PolicyConstraint):

  def is_default_restored(self) -> bool:
    """Indicates that the constraintDefault enforcement behavior is restored."""
    return True


@caching.cached_api_call
def _get_effective_org_policy_all_constraints(
    project_id: str) -> Dict[str, PolicyConstraint]:
  # NOTE: this function doesn't get the "effective" org policy, but just
  # the policies that are directly set on the project. This is a deliberate
  # choice to improve performance.
  #
  # in order to speed up execution, we fetch all constraints that we think
  # could be useful on the first call to get_effective_org_policy()

  # note: it would be probably better to use this API, but then this would
  # require users to enable it :-( :
  # https://cloud.google.com/resource-manager/docs/reference/orgpolicy/rest/v2/projects.policies/getEffectivePolicy
  return get_all_project_org_policies(project_id)


def get_effective_org_policy(project_id: str, constraint: str):
  """Get the effective org policy for a project and a given constraint.

  This function will first try to get the policy from a cached list of all
  policies that are set on the project. If the policy is not found, it will
  make a direct API call to get the effective policy for the given constraint.
  """
  all_constraints = _get_effective_org_policy_all_constraints(project_id)
  if constraint in all_constraints:
    return all_constraints[constraint]

  # If the constraint is not in the list of all policies, it means that
  # the policy is not set on the project. In this case, we need to get the
  # effective policy directly.
  crm_api = apis.get_api('cloudresourcemanager', 'v1', project_id)
  try:
    req = crm_api.projects().getEffectiveOrgPolicy(
        resource=f'projects/{project_id}', body={'constraint': constraint})
    result = req.execute(num_retries=config.API_RETRIES)
  except googleapiclient.errors.HttpError as err:
    raise utils.GcpApiError(err) from err

  if 'booleanPolicy' in result:
    return BooleanPolicyConstraint(result['constraint'],
                                   result['booleanPolicy'])
  elif 'listPolicy' in result:
    return ListPolicyConstraint(result['constraint'], result['listPolicy'])
  else:
    raise ValueError(f'unknown constraint type: {result}')


@caching.cached_api_call
def get_all_project_org_policies(project_id: str):
  """list all the org policies set for a particular resource.

  Args:
      project_id: The project ID.

  Returns:
      A dictionary of PolicyConstraint objects, keyed by constraint name.

  Raises:
      utils.GcpApiError: on API errors.
  """
  crm_api = apis.get_api('cloudresourcemanager', 'v1', project_id)
  resource = f'projects/{project_id}'
  all_constraints: Dict[str, PolicyConstraint] = {}
  logging.debug('listing org policies of %s', project_id)

  request = crm_api.projects().listOrgPolicies(resource=resource)

  while request:
    try:
      response = request.execute(num_retries=config.API_RETRIES)
    except googleapiclient.errors.HttpError as err:
      raise utils.GcpApiError(err) from err

    policies_list = response.get('policies', [])

    for policy in policies_list:
      constraint_name = policy.get('constraint')

      if 'booleanPolicy' in policy:
        all_constraints[constraint_name] = BooleanPolicyConstraint(
            constraint_name, policy['booleanPolicy'])
      elif 'listPolicy' in policy:
        all_constraints[constraint_name] = ListPolicyConstraint(
            constraint_name, policy['listPolicy'])
      elif 'restoreDefault' in policy:
        all_constraints[constraint_name] = RestoreDefaultPolicyConstraint(
            constraint_name, policy['restoreDefault'])
      else:
        logging.warning('unknown constraint type: %s', policy)

    request = crm_api.projects().listOrgPolicies_next(request, response)

  return all_constraints
