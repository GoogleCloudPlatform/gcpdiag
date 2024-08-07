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
"""BigQuery table does not exceed number of partition modifications to a column partitioned table

BigQuery returns this error when your column-partitioned table reaches the quota
of the number of partition modifications permitted per day. Partition
modifications include the total of all load jobs, copy jobs, and query jobs that
append or overwrite a destination partition.
"""
from boltons.iterutils import get_path

from gcpdiag import lint, models
from gcpdiag.queries import apis, crm, logs

MATCH_STR = 'Your table exceeded quota for Number of partition modifications'

QUOTA_EXCEEDED = [
    'severity=ERROR',
    'protoPayload.methodName="jobservice.jobcompleted"',
    'protoPayload.@type="type.googleapis.com/google.cloud.audit.AuditLog"',
    f'protoPayload.status.message:("{MATCH_STR}")',
]
logs_by_project = {}


def prepare_rule(context: models.Context):
  logs_by_project[context.project_id] = logs.query(
      project_id=context.project_id,
      resource_type='bigquery_resource',
      log_name='log_id("cloudaudit.googleapis.com/data_access")',
      filter_str=' AND '.join(QUOTA_EXCEEDED),
  )


def run_rule(context: models.Context, report: lint.LintReportRuleInterface):
  project = crm.get_project(context.project_id)

  # skip entire rule is logging disabled
  if not apis.is_enabled(context.project_id, 'logging'):
    report.add_skipped(project, 'logging api is disabled')
    return

  if not apis.is_enabled(context.project_id, 'bigquery'):
    report.add_skipped(project, 'bigquery api is disabled')
    return

  if (logs_by_project.get(context.project_id) and
      logs_by_project[context.project_id].entries):
    for log_entry in logs_by_project[context.project_id].entries:
      # Filter out non-relevant log entries.
      if log_entry['severity'] != 'ERROR' or MATCH_STR not in get_path(
          log_entry, ('protoPayload', 'status', 'message'), default=''):
        continue
      job_id = get_path(
          log_entry,
          (
              'protoPayload',
              'serviceData',
              'jobCompletedEvent',
              'job',
              'jobName',
              'jobId',
          ),
      )
      report.add_failed(
          project,
          'Exceeded quota for number of partition modifications per'
          ' column-partitioned table per day. Please check failed job ' +
          job_id + ' for more details.',
      )
      return
  # in case of there is no log or all logs are non-relevant
  report.add_ok(project)
