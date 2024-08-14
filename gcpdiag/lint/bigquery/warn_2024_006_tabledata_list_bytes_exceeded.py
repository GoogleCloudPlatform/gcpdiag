#
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
"""BigQuery job does not exceed tabledata.list bytes per second per project

BigQuery returns this error when the project number mentioned in the error
message reaches the maximum size of data that can be read through the
tabledata.list API call in a project per second.
"""

from boltons.iterutils import get_path

from gcpdiag import lint, models
from gcpdiag.queries import apis, crm, logs

MATCH_STR = 'tabledata.list bytes per second per project'
LOG_FILTER = [
    'severity>=ERROR',
    'protoPayload.@type="type.googleapis.com/google.cloud.audit.AuditLog"',
    f'protoPayload.status.message:("{MATCH_STR}")',
]

project_logs = {}


def prepare_rule(context: models.Context):
  project_logs[context.project_id] = logs.query(
      project_id=context.project_id,
      resource_type='bigquery_resource',
      log_name='log_id("cloudaudit.googleapis.com/data_access")',
      filter_str=' AND '.join(LOG_FILTER),
  )


def run_rule(context: models.Context, report: lint.LintReportRuleInterface):
  project = crm.get_project(context.project_id)
  # skip entire rule if logging is disabled
  if not apis.is_enabled(context.project_id, 'logging'):
    report.add_skipped(project, 'Logging api is disabled')
    return
  # skip entire rule if the BigQuery API is disabled
  if not apis.is_enabled(context.project_id, 'bigquery'):
    report.add_skipped(project, 'BigQuery api is disabled')
    return
  if (project_logs.get(context.project_id) and
      project_logs[context.project_id].entries):

    for log_entry in project_logs[context.project_id].entries:
      # Filter out non-relevant log entries.
      if log_entry['severity'] != 'ERROR' or MATCH_STR not in get_path(
          log_entry, ('protoPayload', 'status', 'message'), default=''):
        continue

      job_id = get_path(
          log_entry,
          (
              'protoPayload',
              'serviceData',
              'jobGetQueryResultsResponse',
              'job',
              'jobName',
              'jobId',
          ),
      )

      report.add_failed(
          project,
          'Exceeded maximum tabledata.list bytes per second per project'
          ' limit. Try spacing out requests over a longer period with'
          ' delays. Please check failed job ' + job_id + ' for more details.',
      )
      return
    report.add_ok(project)
