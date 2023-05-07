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
from typing import Dict

from gcpdiag import caching
from gcpdiag.queries import apis, apis_utils

PREFETCH_ORG_CONSTRAINTS = (
    'constraints/compute.disableSerialPortAccess',
    'constraints/compute.requireOsLogin',
    'constraints/compute.requireShieldedVm',
    'constraints/iam.automaticIamGrantsForDefaultServiceAccounts')

# TODO: list policy constraints of interest (not yet supported)
# 'constraints/compute.vmCanIpForward'
# 'restrictSharedVpcSubnetworks'


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
  logging.info('getting org constraints of %s', project_id)
  for _, result, exception in apis_utils.batch_execute_all(crm_api, requests):
    if exception:
      logging.warning("can't retrieve org contraint (error: %s)", exception)
      continue
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
