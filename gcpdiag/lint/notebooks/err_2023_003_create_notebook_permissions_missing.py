# Copyright 2023 Google LLC
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
"""Vertex AI Workbench account has required permissions to create and use notebooks

Creating and using a notebook requires service-*@gcp-sa-notebooks.iam.gserviceaccount.com
to have "AI Platform Notebooks Service Agent" role and for user to have "Service Account User" role
"""

from boltons.iterutils import get_path

from gcpdiag import lint, models
from gcpdiag.queries import apis, crm, logs

MATCH_STRING = 'permission'

NOTEBOOKS_SA = '^service-.*@gcp-sa-notebooks.iam.gserviceaccount.com$'

NOTEBOOKS_MISSING_PERMISSIONS_FILTER = [
    'severity=ERROR',
    'protoPayload.serviceName = "notebooks.googleapis.com"',
    f'protoPayload.status.message =~ "{MATCH_STRING}"',
    'protoPayload.status.code = 7',
]

COMPUTE_ENGINE_MISSING_PERMISSIONS_FILTER = [
    'severity=ERROR',
    'protoPayload.serviceName = "compute.googleapis.com"',
    'protoPayload.authorizationInfo.granted != True',
    f'protoPayload.authenticationInfo.principalEmail =~ "{NOTEBOOKS_SA}"',
    f'protoPayload.status.message =~ "{MATCH_STRING}"',
    'protoPayload.status.code = 7',
]

logs_by_project_notebooks = {}
logs_by_project_compute = {}


def prepare_rule(context: models.Context):
  project_id = context.project_id

  log_name = 'log_id("cloudaudit.googleapis.com/activity")'

  logs_by_project_notebooks[context.project_id] = logs.query(
      project_id=project_id,
      log_name=log_name,
      resource_type='audited_resource',
      filter_str=' AND '.join(NOTEBOOKS_MISSING_PERMISSIONS_FILTER))

  logs_by_project_compute[context.project_id] = logs.query(
      project_id=project_id,
      log_name=log_name,
      resource_type='gce_instance',
      filter_str=' AND '.join(COMPUTE_ENGINE_MISSING_PERMISSIONS_FILTER))


def find_logs_with_permission_errors(context: models.Context,
                                     logs_by_project: dict):
  if (logs_by_project.get(context.project_id) and
      logs_by_project[context.project_id].entries):
    for log_entry in logs_by_project[context.project_id].entries:
      # Filter out non-relevant and repeated log entries.
      if (log_entry['severity'] == 'ERROR' and MATCH_STRING in get_path(
          log_entry, ('protoPayload', 'status', 'message'), default='')):
        return True
  return False


def run_rule(context: models.Context, report: lint.LintReportRuleInterface):
  project = crm.get_project(context.project_id)

  # skip entire rule is logging disabled
  if not apis.is_enabled(context.project_id, 'logging'):
    report.add_skipped(project, 'Logging API is disabled')
    return

  if not apis.is_enabled(context.project_id, 'notebooks'):
    report.add_skipped(project, 'Notebooks API is disabled')
    return

  # Logs-based rule as any user account or SA can create/use/own notebooks
  if (find_logs_with_permission_errors(context, logs_by_project_notebooks) or
      find_logs_with_permission_errors(context, logs_by_project_compute)):
    report.add_failed(
        project,
        ('Missing permissions: '
         '@gcp-sa-notebooks.iam.gserviceaccount.com Service Account must '
         'have "AI Platform Notebooks Service Agent" role and user account '
         'must have "Service Acount User" role'))
  else:
    report.add_ok(project)
