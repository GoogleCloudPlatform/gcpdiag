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
Cloud Data Fusion Service Account exists

Cloud Data Fusion Service Account fetched from a Cloud Data Fusion instance
is missing at a Project's IAM policy
"""

from gcpdiag import lint, models
from gcpdiag.queries import apis, crm, datafusion, iam

projects_instances = {}
IAM_ROLE = 'roles/iam.serviceAccountUser'


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
    report.add_skipped(None, 'Cloud Data Fusion instances were not found')
    return
  project_id = context.project_id
  for _, datafusion_instance in sorted(datafusion_instances.items()):
    iam_policy = iam.get_project_policy(project_id)
    project_id = context.project_id
    p4sa = datafusion_instance.api_service_agent
    if not p4sa:
      report.add_skipped(
          None, f'{datafusion_instance.name} '
          f'does not have Cloud Data Fusion Service Account')
      continue
    datafusion_sa = 'serviceAccount:' + p4sa
    members = iam_policy.get_members()
    result = datafusion_sa in members
    if not result:
      report.add_failed(
          datafusion_instance,
          f'{datafusion_sa} missing or does not exist at project')
    else:
      report.add_ok(datafusion_instance)
