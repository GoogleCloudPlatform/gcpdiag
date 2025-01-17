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
"""Contains Generatlized Steps for IAM"""

from typing import Optional, Set

from gcpdiag import runbook
from gcpdiag.queries import iam
from gcpdiag.runbook import op
from gcpdiag.runbook.iam import flags


class VmHasAnActiveServiceAccount(runbook.Step):
  """Investigates if a VM's service account is active.

  This step checks if the specified service account is neither disabled nor deleted.
  It verifies the existence of the service account and its active status within
  the specified project.

  Attributes:
    template (str): Template identifier for reporting the service account status.
    service_account (str, optional): The email address of the service account to check.
                                     If not provided, it is obtained from the operation's context.
    project_id (str, optional): The ID of the Google Cloud project within which to check
                                the service account. If not provided, it is obtained from
                                the operation's context.
  """

  template = 'service_account::active'
  service_account: str = ''
  project_id: str = ''

  def execute(self):
    """Verify if the specified service account is active."""
    sa = self.service_account or op.get(flags.SERVICE_ACCOUNT)
    project_id = self.project_id or op.get(flags.PROJECT_ID)

    if sa and project_id:
      sa_resource = next(
          filter(lambda r: r.email == sa,
                 iam.get_service_account_list(project_id)), None)
      # Verify service account exists
      if not iam.is_service_account_existing(sa, project_id):
        op.add_failed(sa_resource,
                      reason=op.prep_msg(op.FAILURE_REASON, sa=sa),
                      remediation=op.prep_msg(op.FAILURE_REMEDIATION))
      # Verify service account exists
      elif not iam.is_service_account_enabled(sa, project_id):
        op.add_failed(resource=sa_resource,
                      reason=op.prep_msg(op.FAILURE_REASON),
                      remediation=op.prep_msg(op.FAILURE_REMEDIATION_ALT1,
                                              sa=sa))
      elif (iam.is_service_account_existing(sa, project_id) and
            iam.is_service_account_enabled(sa, project_id)):
        op.add_ok(sa_resource, op.prep_msg(op.SUCCESS_REASON, sa=sa))
      else:
        op.add_uncertain(None,
                         reason=op.UNCERTAIN_REASON,
                         remediation=op.prep_msg(op.UNCERTAIN_REMEDIATION))
    else:
      op.add_uncertain(None,
                       reason=op.UNCERTAIN_REASON,
                       remediation=op.prep_msg(op.UNCERTAIN_REMEDIATION))


class IamPolicyCheck(runbook.Step):
  """Checks if a principal has specified permissions or is a member of specified roles.

  This step supports checking for either all specified permissions/roles are present or
  at least one for the principal (user or service account). It reports the present and missing
  permissions/roles accordingly. Also, identifying which permissions or roles
  are present and which are missing.

  Attributes:
    principal (str): The identifier for the principal whose permissions are being checked.
    permissions (Optional[Set[str]]): A set of IAM permissions to check. Specify this or `roles`.
    roles (Optional[Set[str]]): A set of IAM roles to check. Specify this or `permissions`.
    require_all (bool): If True, requires all specified permissions or roles to be present. If
                        False, requires at least one of the specified permissions or roles to be
                        present.
    template (str): The template used for generating reports for the step.
  """
  template = 'permissions::default'

  principal: str = ''
  permissions: Optional[Set[str]] = None
  roles: Optional[Set[str]] = None
  require_all: bool = False
  project = None

  def execute(self):
    """Verify IAM policy"""
    project_id = self.project or op.get(flags.PROJECT_ID)
    iam_policy = iam.get_project_policy(project_id)
    principal = self.principal or op.get(flags.PRINCIPAL)
    present_permissions_or_roles = set()
    missing_permissions_or_roles = set()
    items = self.permissions or self.roles or set()

    for item in items:
      if self.permissions:
        has_item = iam_policy.has_permission(principal, item)
      else:
        has_item = iam_policy.has_role_permissions(principal, item)
      if has_item:
        present_permissions_or_roles.add(item)
      else:
        missing_permissions_or_roles.add(item)

    all_present = not missing_permissions_or_roles
    any_present = bool(present_permissions_or_roles)
    outcome = all_present if self.require_all else any_present

    permissions_or_roles = 'permissions' if self.permissions else 'roles'

    if outcome:
      op.add_ok(resource=iam_policy,
                reason=op.prep_msg(op.SUCCESS_REASON,
                                   principal=principal,
                                   permissions_or_roles=permissions_or_roles,
                                   present_permissions_or_roles=', '.join(
                                       sorted(present_permissions_or_roles))))
    else:
      op.add_failed(
          resource=iam_policy,
          reason=op.prep_msg(op.FAILURE_REASON,
                             principal=principal,
                             permissions_or_roles=permissions_or_roles,
                             missing_permissions_or_roles=', '.join(
                                 sorted(missing_permissions_or_roles))),
          remediation=op.prep_msg(op.FAILURE_REMEDIATION,
                                  principal=principal,
                                  permissions_or_roles=permissions_or_roles,
                                  present_permissions_or_roles=', '.join(
                                      sorted(present_permissions_or_roles)),
                                  missing_permissions_or_roles=', '.join(
                                      sorted(missing_permissions_or_roles))))
