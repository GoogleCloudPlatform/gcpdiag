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
"""Data Transfer Service Agent exists and has the required roles.

Verify that the BigQuery Data Transfer service agent exists and has been granted
the roles/bigquerydatatransfer.serviceAgent role.
"""

from gcpdiag import lint, models
from gcpdiag.queries import apis, crm, iam

ROLE = 'roles/bigquerydatatransfer.serviceAgent'


def run_rule(context: models.Context,
             report: lint.LintReportRuleInterface) -> None:
  project = crm.get_project(context.project_id)

  if not apis.is_enabled(context.project_id, 'bigquery'):
    report.add_skipped(project, 'bigquery api is disabled')
    return

  if not apis.is_enabled(context.project_id, 'bigquerydatatransfer'):
    report.add_skipped(project, 'bigquery data transfer api is disabled')
    return

  policy = iam.get_project_policy(context.project_id)
  dts_sa = f'service-{project.number}@gcp-sa-bigquerydatatransfer.iam.gserviceaccount.com'

  if iam.is_service_account_existing(dts_sa, context.project_id):
    if policy.has_role_permissions(f'serviceAccount:{dts_sa}', ROLE):
      report.add_ok(project)
    else:
      report.add_failed(project, (f'service account: {dts_sa}\n'
                                  f'missing role: {ROLE}'))
  else:
    report.add_failed(project, (f'service account: {dts_sa} is missing'))
