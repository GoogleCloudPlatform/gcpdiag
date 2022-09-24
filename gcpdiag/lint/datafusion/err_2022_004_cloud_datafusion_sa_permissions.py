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
"""Cloud Data Fusion Service Account permissions

Verify that the Cloud Data Fusion Service Agent account exists and has
the Cloud Data Fusion Service Agent role on the project.
"""

from gcpdiag import lint, models
from gcpdiag.queries import apis, crm, iam

DATAFUSION_ROLE = 'roles/datafusion.serviceAgent'

policies_by_project = {}


def prefetch_rule(context: models.Context):
  policies_by_project[context.project_id] = iam.get_project_policy(
      context.project_id)


def run_rule(context: models.Context, report: lint.LintReportRuleInterface):
  project_id = context.project_id
  project = crm.get_project(project_id)
  datafusion_sa = f'service-{project.number}@gcp-sa-datafusion.iam.gserviceaccount.com'
  if not apis.is_enabled(project_id, 'datafusion'):
    report.add_skipped(None,
                       f'Cloud Data Fusion API is not enabled in {project}')
    return
  if not policies_by_project[project_id].has_role_permissions(
      f'serviceAccount:{datafusion_sa}', DATAFUSION_ROLE):
    report.add_failed(
        project,
        f'The Cloud Data Fusion Service Account is missing {DATAFUSION_ROLE} or does not exist'
    )
  else:
    report.add_ok(project, f'\n{datafusion_sa} has {DATAFUSION_ROLE}')
