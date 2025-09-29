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

# Lint as: python3
"""Cloud Functions service agent has the cloudfunctions.serviceAgent role.

The Cloud Functions Service Agent is missing the cloudfunctions.serviceAgent role,
which gives Cloud Functions Service Agent access to managed resources.
You can resolve this error by granting the cloudfunctions.serviceAgent IAM role
to service-PROJECT_NUMBER@gcf-admin-robot.iam.gserviceaccount.com.
"""

from gcpdiag import lint, models
from gcpdiag.queries import crm, gcf, iam

ROLE = 'roles/cloudfunctions.serviceAgent'


def run_rule(context: models.Context, report: lint.LintReportRuleInterface):
  cloudfunctions = gcf.get_cloudfunctions(context)
  if not cloudfunctions:
    report.add_skipped(None, f'no functions found {context}')
    return

  project = crm.get_project(context.project_id)
  sa_email = f'service-{project.number}@gcf-admin-robot.iam.gserviceaccount.com'
  iam_policy = iam.get_project_policy(context)
  if not iam_policy.has_role_permissions(f'serviceAccount:{sa_email}', ROLE):
    report.add_failed(project,
                      f'service account: {sa_email}\nmissing role: {ROLE}')
  else:
    report.add_ok(project)
