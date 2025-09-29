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
"""
Cloud Data Fusion SA has Service Account User permissions on the Dataproc SA.

Cloud Data Fusion Service Account is missing Service Account User permissions
on the Dataproc service account associated with the Data Fusion instance.
"""

from gcpdiag import lint, models
from gcpdiag.queries import apis, crm, datafusion, iam

IAM_ROLE = 'roles/iam.serviceAccountUser'

projects_instances = {}


def prefetch_rule(context: models.Context):
  projects_instances[context.project_id] = datafusion.get_instances(context)


def run_rule(context: models.Context, report: lint.LintReportRuleInterface):
  if not apis.is_enabled(context.project_id, 'datafusion'):
    report.add_skipped(
        None,
        f'Cloud Data Fusion API is not enabled in {crm.get_project(context.project_id)}'
    )
    return
  datafusion_instances = projects_instances[context.project_id]
  if not datafusion_instances:
    report.add_skipped(None,
                       f'no Cloud Data Fusion instances were found {context}')
    return

  iam_policy = iam.get_project_policy(context)
  constructed_datafusion_sa = ('serviceAccount:service-{project_number}'
                               '@gcp-sa-datafusion.iam.gserviceaccount.com')
  project_iam_policy_result = iam_policy.has_role_permissions(
      constructed_datafusion_sa, IAM_ROLE)

  for _, datafusion_instance in sorted(datafusion_instances.items()):
    dataproc_service_account = datafusion_instance.dataproc_service_account
    if not dataproc_service_account:
      report.add_skipped(
          None, f'{datafusion_instance.name} '
          'does not have DataProc Service Account')
      continue
    service_account_iam_policy = iam.get_service_account_iam_policy(
        context, dataproc_service_account)
    p4sa = datafusion_instance.api_service_agent
    datafusion_sa = 'serviceAccount:' + p4sa
    sa_iam_policy_result = service_account_iam_policy.has_role_permissions(
        datafusion_sa, IAM_ROLE)
    if project_iam_policy_result or sa_iam_policy_result:
      report.add_ok(datafusion_instance)
    else:
      report.add_failed(
          datafusion_instance, f'{datafusion_sa}\nlacks {IAM_ROLE} '
          f'on DataProc SA ({dataproc_service_account}) associated with '
          f'{datafusion_instance.name}')
