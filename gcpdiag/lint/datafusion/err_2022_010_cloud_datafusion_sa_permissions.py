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
Cloud Dataproc Service Account has a Dataproc Worker role.

Cloud Dataproc Service Account associated with a Cloud DataFusion instance is
missing a Dataproc Worker role at the Project's IAM policy.
"""

from gcpdiag import lint, models
from gcpdiag.queries import apis, crm, datafusion, iam

DP_WORKER = 'roles/dataproc.worker'

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
                       f'no Cloud Data Fusion instances not found {context}')
    return

  iam_policy = iam.get_project_policy(context)

  for _, datafusion_instance in sorted(datafusion_instances.items()):
    instance_dataproc_sa = datafusion_instance.dataproc_service_account
    if not instance_dataproc_sa:
      report.add_skipped(
          None, f'{datafusion_instance.name} '
          'does not have Dataproc Service Account')
      continue
    dataproc_sa = 'serviceAccount:' + instance_dataproc_sa
    project_policy_result = iam_policy.has_role_permissions(
        dataproc_sa, DP_WORKER)
    if project_policy_result:
      report.add_ok(datafusion_instance)
    else:
      report.add_failed(datafusion_instance, f'{dataproc_sa} lacks {DP_WORKER}')
