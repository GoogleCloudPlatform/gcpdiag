# Copyright 2024 Google LLC
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
"""Vertex AI Workbench Notebooks Executor code uses explicit project selection

Running a notebook code execution requires user to explicitly set client
libraries with the user's project to avoid 40X errors with the executor project
"""

from boltons.iterutils import get_path

from gcpdiag import lint, models
from gcpdiag.queries import apis, crm, logs

ERROR_CODE = '40'
ERROR_MESSAGE = 'permission'

ERROR_MESSAGE_MATCH_STRING_1 = (
    f'{ERROR_CODE}[4,3] (GET|POST) '
    r'https:\/\/bigquery.googleapis.com\/bigquery\/[a-z0-9.]*\/projects\/[a-z0-9]{1,20}-tp'
)

ERROR_MESSAGE_MATCH_STRING_2 = (
    'does not have '
    f'[a-z.]* {ERROR_MESSAGE} in project [a-z0-9]{1,20}-tp')

ERROR_MESSAGE_MATCH_STRING_3 = fr'{ERROR_CODE}[3,4] gs:\/\/[a-z0-9]{1,20}-tp'

ERROR_MESSAGES = (
    f'(jsonPayload.message =~ "{ERROR_MESSAGE_MATCH_STRING_1}" OR '
    f'jsonPayload.message =~ "{ERROR_MESSAGE_MATCH_STRING_2}" OR '
    f'jsonPayload.message =~ "{ERROR_MESSAGE_MATCH_STRING_3}")')

NOTEBOOKS_EXECUTOR_PERMISSIONS_ERRORS_FILTER = [
    'severity=ERROR',
    'labels."compute.googleapis.com/resource_name" =~ "training"',
    ERROR_MESSAGES
]

logs_by_project = {}


def prepare_rule(context: models.Context):
  project_id = context.project_id

  log_name = 'log_id("workerpool0-0")'

  logs_by_project[context.project_id] = logs.query(
      project_id=project_id,
      log_name=log_name,
      resource_type='ml_job',
      filter_str=' AND '.join(NOTEBOOKS_EXECUTOR_PERMISSIONS_ERRORS_FILTER),
  )


def find_logs_with_permission_errors(context: models.Context):
  if (logs_by_project.get(context.project_id) and
      logs_by_project[context.project_id].entries):
    for log_entry in logs_by_project[context.project_id].entries:
      # Filter out non-relevant and repeated log entries.
      path_message = get_path(log_entry, ('jsonPayload', 'message'), default='')
      if log_entry['severity'] == 'ERROR' and (ERROR_CODE in path_message or
                                               ERROR_MESSAGE in path_message):
        return True
  return False


def run_rule(context: models.Context, report: lint.LintReportRuleInterface):
  project = crm.get_project(context.project_id)

  # skip entire rule if logging is disabled
  if not apis.is_enabled(context.project_id, 'logging'):
    report.add_skipped(project, 'Logging API is disabled')
    return

  if not apis.is_enabled(context.project_id, 'notebooks'):
    report.add_skipped(project, 'Notebooks API is disabled')
    return

  if not apis.is_enabled(context.project_id, 'aiplatform'):
    # Notebooks executor depends on Vertex AI API
    report.add_skipped(project, 'Vertex API is disabled')
    return

  # Logs-based rule as error only occurs at runtime and depends on user code
  if find_logs_with_permission_errors(context):
    report.add_failed(
        project,
        ('Missing permissions in executor project: You did not specify your'
         'own project id explicitly in your notebook code'),
    )
  else:
    report.add_ok(project)
