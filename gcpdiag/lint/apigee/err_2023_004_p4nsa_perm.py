# Copyright 2023 Google LLC
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
"""Service Networking API is enabled and SA account has the required role


1. Service networking API needs to be enabled
2. Service Agent(SA) account
[service-{project_number}@service-networking.iam.gserviceaccount.com]
needs to have the Networking Service Agent role
[roles/servicenetworking.serviceAgent] on the project.
"""

from gcpdiag import lint, models
from gcpdiag.queries import apigee, apis, crm, iam

SA = 'service-{project_number}@service-networking.iam.gserviceaccount.com'
ROLE = 'roles/servicenetworking.serviceAgent'


def run_rule(context: models.Context, report: lint.LintReportRuleInterface):
  apigee_org = apigee.get_org(context)
  if apigee_org is None:
    report.add_skipped(None, 'no Apigee organizations found')
    return

  project_id = context.project_id
  project = crm.get_project(context.project_id)
  service_account = SA.format(project_number=project.number)

  # Check if Service Networking API is enabled
  if not apis.is_enabled(project_id, 'servicenetworking'):
    report.add_failed(project, 'Service Networking API is not enabled')

  else:
    # Check if Service Agent role is assigned to the SA account
    iam_policy = iam.get_project_policy(context.project_id)
    if not iam_policy.has_role_permissions(f'serviceAccount:{service_account}',
                                           ROLE):
      report.add_failed(
          project, f'service account: {service_account}\nmissing role: {ROLE}')
    else:
      report.add_ok(project)
