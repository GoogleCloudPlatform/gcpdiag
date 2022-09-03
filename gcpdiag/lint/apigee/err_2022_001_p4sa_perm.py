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
"""Apigee Service Agent permissions

Verify that the Apigee Service Agent account exists and has
the Apigee Service Agent role on the project.
"""

from gcpdiag import lint, models
from gcpdiag.queries import apigee, crm, iam

SA = 'service-{project_number}@gcp-sa-apigee.iam.gserviceaccount.com'
ROLE = 'roles/apigee.serviceAgent'


def run_rule(context: models.Context, report: lint.LintReportRuleInterface):
  apigee_org = apigee.get_org(context)
  if apigee_org is None:
    report.add_skipped(None, 'no Apigee organizations found')
    return

  project = crm.get_project(context.project_id)
  service_account = SA.format(project_number=project.number)

  iam_policy = iam.get_project_policy(context.project_id)
  if not iam_policy.has_role_permissions(f'serviceAccount:{service_account}',
                                         ROLE):
    report.add_failed(project, (f'service account: {service_account}\n'
                                f'missing role: {ROLE}'))
  else:
    report.add_ok(project)
