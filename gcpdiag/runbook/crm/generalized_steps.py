# Copyright 2024 Google LLC
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
"""Contains Generatlized Steps for Cloud Resource Manager"""

from gcpdiag import runbook
from gcpdiag.queries import crm, orgpolicy
from gcpdiag.runbook import op
from gcpdiag.runbook.iam import constants, flags


class OrgPolicyCheck(runbook.Step):
  """Checks if an organization policy is effective in a project

  Supports only boolean constraints and not list constraints.
  """
  template = 'orgpolicy::default'
  constraint: str
  is_enforced: bool = True
  project = None

  def execute(self):
    """Checking Organization policy"""
    project_id = self.project or op.get(flags.PROJECT_ID)
    project = crm.get_project(project_id)
    constraint = orgpolicy.get_effective_org_policy(project_id, self.constraint)

    expected_state = 'enforced' if self.is_enforced else 'not enforced'
    actual_state = 'enforced' if constraint.is_enforced() else 'not enforced'

    # Is effected to be enforced and is enforce or vice versa
    if (self.is_enforced and
        constraint.is_enforced()) or (not self.is_enforced and
                                      not constraint.is_enforced()):
      op.add_ok(resource=project,
                reason=op.prep_msg(op.SUCCESS_REASON,
                                   constraint=self.constraint,
                                   expected_state=expected_state,
                                   actual_state=actual_state))

    # Is effected to be enforced and is enforce or vice versa
    elif (self.is_enforced and
          not constraint.is_enforced()) or (not self.is_enforced and
                                            constraint.is_enforced()):
      op.add_failed(resource=project,
                    reason=op.prep_msg(constants.FAILURE_REASON,
                                       constraint=self.constraint,
                                       expected_state=expected_state,
                                       actual_state=actual_state),
                    remediation=op.prep_msg(constants.FAILURE_REMEDIATION))
