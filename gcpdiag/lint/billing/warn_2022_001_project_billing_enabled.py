#
# Copyright 2021 Google LLC
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

# Lint as: python3
"""Projects have billing enabled

Check whether all projects the user has permission to view have billing enabled.

"""

from gcpdiag import lint, models
from gcpdiag.queries import apis, billing, crm

all_project_billing_info = []


def prepare_rule(context: models.Context):
  all_project_billing_info.extend(
      crm.get_all_projects_in_parent(context.project_id))


def run_rule(context: models.Context, report: lint.LintReportRuleInterface):
  if not apis.is_enabled(context.project_id, 'cloudbilling'):
    # an API error is raised
    billing.get_billing_info(context.project_id)
    return
  if len(all_project_billing_info) == 0:
    report.add_skipped(None, 'Permission Denied')
    return
  for project_billing_info in all_project_billing_info:
    project = crm.get_project(project_billing_info.project_id)
    if not project_billing_info.is_billing_enabled():
      report.add_failed(project)
      return
  # all projects have billing enabled
  report.add_ok(crm.get_project(context.project_id))
