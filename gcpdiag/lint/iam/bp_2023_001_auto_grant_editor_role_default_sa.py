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
"""Policy constraint AutomaticIamGrantsForDefaultServiceAccounts is enforced

Policy constraint AutomaticIamGrantsForDefaultServiceAccounts is strongly recommended to be
enforced in production projects according to security best practices.
"""

from gcpdiag import lint, models
from gcpdiag.queries import crm, orgpolicy

constraints = None


def prefetch_rule(context: models.Context):
  global constraints
  constraints = orgpolicy.get_effective_org_policy(
      context.project_id,
      "constraints/iam.automaticIamGrantsForDefaultServiceAccounts")


def run_rule(context: models.Context, report: lint.LintReportRuleInterface):
  project = crm.get_project(context.project_id)
  if not constraints:
    report.add_failed(project)
  elif constraints.is_enforced():
    report.add_ok(project)
  else:
    report.add_failed(project)
