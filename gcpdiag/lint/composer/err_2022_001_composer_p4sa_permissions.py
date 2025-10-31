# Copyright 2022 Google LLC
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
"""Composer Service Agent permissions

Verify that the Cloud Composer Service Agent account exists and has
the Cloud Composer Service Agent role on the project.
"""

from gcpdiag import lint, models
from gcpdiag.queries import apis, crm, iam

SA = 'service-{project_number}@cloudcomposer-accounts.iam.gserviceaccount.com'
ROLE = 'roles/composer.serviceAgent'

projects = {}
policy_by_project = {}


def prefetch_rule(context: models.Context):
  projects[context.project_id] = crm.get_project(context.project_id)
  policy_by_project[context.project_id] = iam.get_project_policy(context)


def run_rule(context: models.Context, report: lint.LintReportRuleInterface):
  if not apis.is_enabled(context.project_id, 'composer'):
    report.add_skipped(None, 'composer is disabled')
    return

  project = projects[context.project_id]
  service_account = SA.format(project_number=project.number)

  project_policy = policy_by_project[context.project_id]
  if not project_policy.has_role_permissions(
      f'serviceAccount:{service_account}', ROLE):
    report.add_failed(project, (f'service account: {service_account}\n'
                                f'missing role: {ROLE}'))
    return

  report.add_ok(project)
