# Copyright 2025 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# Lint as: python3
"""Number of expensive Looker Studio bigquery job.
Checking BigQuery jobs associated with Looker Studio which are billed over 1 GB"""
from boltons.iterutils import get_path  # type: ignore

from gcpdiag import lint, models
from gcpdiag.queries import apis, crm, logs

HIGHLY_EXTENSIVE_FILTER = [
    'protoPayload.methodName="jobservice.jobcompleted"',
    ('protoPayload.serviceData.jobCompletedEvent.job.'
     'jobStatistics.totalBilledBytes>="1073741824"'),
    ('protoPayload.serviceData.jobCompletedEvent.job.'
     'jobConfiguration.labels.reques'
     'tor="looker_studio"')
]
logs_by_project = {}


def prepare_rule(context: models.Context):
  logs_by_project[context.project_id] = logs.query(
      project_id=context.project_id,
      resource_type='bigquery_resource',
      log_name='log_id("cloudaudit.googleapis.com/data_access")',
      filter_str=' '.join(HIGHLY_EXTENSIVE_FILTER),
  )


def run_rule(
    context: models.Context,
    report: lint.LintReportRuleInterface,
):
  job_counts: dict[str, int] = {}

  project = crm.get_project(context.project_id)
  # skip entire rule if logging disabled
  if not apis.is_enabled(context.project_id, 'logging'):
    report.add_skipped(project, 'logging api is disabled')
    return
  if not apis.is_enabled(context.project_id, 'bigquery'):
    report.add_skipped(project, 'bigquery api is disabled')
    return
  if logs_by_project.get(
      context.project_id) and logs_by_project[context.project_id].entries:
    for log_entry in logs_by_project[context.project_id].entries:
      email_id = get_path(
          log_entry,
          (
              'protoPayload',
              'authenticationInfo',
              'principalEmail',
          ),
      )
      if email_id:
        job_counts[email_id] = job_counts.get(email_id, 0) + 1
    for email_id, count in job_counts.items():
      report.add_failed(
          project,
          f'The user {email_id} ran {count} BigQuery jobs in LSP billed over 1 GB'
      )
    return
  # in case of there is no log or all logs are non-relevant
  else:
    report.add_ok(
        project,
        'No BigQuery jobs billed over 1 GB from Looker Studio were found.')
