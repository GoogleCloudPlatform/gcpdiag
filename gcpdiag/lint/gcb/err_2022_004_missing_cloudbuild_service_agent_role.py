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

# Lint as: python3
"""Cloud Build Service Agent has the cloudbuild.serviceAgent role.

The Cloud Build Service Agent is missing the cloudbuild.serviceAgent role,
which gives Cloud Build service account access to managed resources.
You can resolve this error by granting the Cloud Build Service Agent
(roles/cloudbuild.serviceAgent) IAM role
to service-[PROJECT_NUMBER]@gcp-sa-cloudbuild.iam.gserviceaccount.com.
"""

from gcpdiag import lint, models
from gcpdiag.queries import crm, gcb, iam

ROLE = 'roles/cloudbuild.serviceAgent'


def run_rule(context: models.Context, report: lint.LintReportRuleInterface):
  triggers = gcb.get_triggers(context)
  if not triggers:
    report.add_skipped(None, 'no triggers found')
    return
  project_id = context.project_id
  project = crm.get_project(context.project_id)
  sa_email = f'service-{project.number}@gcp-sa-cloudbuild.iam.gserviceaccount.com'
  iam_policy = iam.get_project_policy(project_id)
  if not iam_policy.has_role_permissions(f'serviceAccount:{sa_email}', ROLE):
    report.add_failed(project,
                      f'service account: {sa_email}\nmissing role: {ROLE}')
  else:
    report.add_ok(project)
