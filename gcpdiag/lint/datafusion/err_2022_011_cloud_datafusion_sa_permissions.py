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
The Dataproc SA for a CDF instance with version > 6.2.0 has Storage Admin role.

The Dataproc Service Account associated with a Cloud Data Fusion instance with
version > 6.2.0 is missing the Cloud Storage Admin role
"""

from packaging import version

from gcpdiag import lint, models
from gcpdiag.queries import apis, crm, datafusion, iam

STORAGE_ADMIN = 'roles/storage.admin'

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
                       f'Cloud Data Fusion instances were not found {context}')
    return
  iam_policy = iam.get_project_policy(context)
  for datafusion_instance in sorted(datafusion_instances.values()):
    instance_dataproc_sa = datafusion_instance.dataproc_service_account
    if not instance_dataproc_sa:
      report.add_skipped(
          None, f'{datafusion_instance.name} '
          f'does not have DataProc Service Account')
    df_instance_version = datafusion_instance.version
    if version.parse(str(df_instance_version)) < version.parse('6.2.0'):
      report.add_skipped(None,
                         'Rule only applicable for datafusion version >=6.2.0')
      continue
    dataproc_sa = 'serviceAccount:' + instance_dataproc_sa
    project_policy_result = iam_policy.has_role_permissions(
        dataproc_sa, STORAGE_ADMIN)
    if project_policy_result:
      report.add_ok(datafusion_instance)
    else:
      report.add_failed(datafusion_instance,
                        f'{dataproc_sa} lacks {STORAGE_ADMIN}')
