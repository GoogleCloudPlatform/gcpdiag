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
"""No service accounts have the Owner role

A Service account should not have a role that could potentially increase the security risk
to the project to malicious activity
"""

from gcpdiag import lint, models
from gcpdiag.queries import crm, iam

ROLE = 'roles/owner'


def prefetch_rule(context: models.Context):
  # Make sure that we have the IAM policy in cache.
  iam.get_project_policy(context.project_id)


def run_rule(context: models.Context, report: lint.LintReportRuleInterface):
  project = crm.get_project(context.project_id)
  iam_policy = iam.get_project_policy(context.project_id)

  for member in sorted(iam_policy.get_members()):
    if member.startswith('serviceAccount:'):
      if iam_policy.has_role_permissions(member, ROLE):
        report.add_failed(project, member + f' has the role {ROLE}')
        break
  else:
    report.add_ok(project)
