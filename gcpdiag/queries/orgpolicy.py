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

PREFETCH_ORG_CONSTRAINTS = (
    'constraints/compute.disableSerialPortAccess',
    'constraints/compute.requireOsLogin',
    'constraints/compute.requireShieldedVm',
    'constraints/iam.automaticIamGrantsForDefaultServiceAccounts',
    'constraints/compute.disableSerialPortLogging',
    'constraints/compute.disableSshInBrowser',
    'constraints/iam.disableCrossProjectServiceAccountUsage',
)


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
  # in order to speed up execution, we fetch all constraints that we think
  # could be useful on the first call to get_effective_org_policy()

  # note: it would be probably better to use this API, but then this would
  # require users to enable it :-( :
  # https://cloud.google.com/resource-manager/docs/reference/orgpolicy/rest/v2/projects.policies/getEffectivePolicy

  crm_api = apis.get_api('cloudresourcemanager', 'v1', project_id)
  requests = []
  for c in PREFETCH_ORG_CONSTRAINTS:
    requests.append(crm_api.projects().getEffectiveOrgPolicy(
        resource=f'projects/{project_id}', body={'constraint': c}))

  all_constraints: Dict[str, PolicyConstraint] = {}
  logging.debug('getting org constraints of %s', project_id)
  for req in requests:
    try:
      result = req.execute(num_retries=config.API_RETRIES)
    except googleapiclient.errors.HttpError as err:
      raise utils.GcpApiError(err) from err

    if 'booleanPolicy' in result:
      all_constraints[result['constraint']] = BooleanPolicyConstraint(
          result['constraint'], result['booleanPolicy'])
    # TODO: list policy constraints
    # elif 'listPolicy' in result:
    #   all_constraints[result['constraint']] = ListPolicyConstraint(
    #       result['constraint'], result['listPolicy'])
    else:
      logging.warning('unknown constraint type: %s', result)

  return all_constraints


def get_effective_org_policy(project_id: str, constraint: str):
  all_constraints = _get_effective_org_policy_all_constraints(project_id)
  if constraint not in all_constraints:
    raise ValueError(
        f'constraint {constraint} not supported {list(all_constraints)}')
  return all_constraints[constraint]


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
