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
"""Dataproc Service Account permissions

Verify that the Dataproc Service Account exists and has the Dataproc Service
Agent role on the project.
"""

from gcpdiag import lint, models
from gcpdiag.queries import crm, dataproc, iam

ROLE = 'roles/dataproc.serviceAgent'
ALT_ROLE = 'roles/editor'


def run_rule(context: models.Context,
             report: lint.LintReportRuleInterface) -> None:
  project = crm.get_project(context.project_id)

  if not dataproc.get_clusters(context):
    report.add_skipped(project, 'no dataproc clusters found')
    return

  policy = iam.get_project_policy(context.project_id)
  dp_sa = f'service-{project.number}@dataproc-accounts.iam.gserviceaccount.com'
  alt_sa = f'{project.number}@cloudservices.gserviceaccount.com'

  if iam.is_service_account_existing(dp_sa, context.project_id):
    if policy.has_role_permissions(f'serviceAccount:{dp_sa}', ROLE):
      report.add_ok(project)
    else:
      report.add_failed(project, (f'service account: {dp_sa}\n'
                                  f'missing role: {ROLE}'))
  else:
    if any(
        policy.has_role_permissions(f'serviceAccount:{alt_sa}', ROLE) or
        policy.has_role_permissions(f'serviceAccount:{alt_sa}', ALT_ROLE)):
      report.add_ok(project)
    else:
      report.add_failed(project, (f'service account: {alt_sa}\n'
                                  f'missing role: {ROLE}'))
