#
# Copyright 2021 Google LLC
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
# pylint: disable=line-too-long
"""Dataflow job is not returning Operation ongoing or Processing Stuck logs.

The Dataflow job will return this warning when your DoFn code is slow, or
waiting for some slow external operation to complete or when your DoFn code
might be stuck, deadlocked, or abnormally slow to finish processing.
"""
# pylint: enable=line-too-long

from itertools import islice

from boltons.iterutils import get_path

from gcpdiag import lint, models
from gcpdiag.queries import apis, crm, logs

MATCH_STRINGS = [
    'Operation ongoing',
    'Processing Stuck',
]
LOG_FILTER = [
    'severity=WARNING',
    'jsonPayload.message: ("{}")'.format('" OR "'.join(MATCH_STRINGS)),
]

project_logs = {}
MAX_JOBS_TO_DISPLAY = 10


def prepare_rule(context: models.Context):
  project_id = context.project_id
  log_name = 'log_id("dataflow.googleapis.com/worker")'
  # f'projects/{project_id}/logs/dataflow.googleapis.com%2Fworker'
  project_logs[project_id] = logs.query(
      project_id=project_id,
      resource_type='dataflow_step',
      log_name=log_name,
      filter_str=' AND '.join(LOG_FILTER),
  )  # "returns LogsQuery object"


def run_rule(context: models.Context, report: lint.LintReportRuleInterface):
  project = crm.get_project(context.project_id)

  # skip entire rule if logging is disabled
  if not apis.is_enabled(context.project_id, 'logging'):
    report.add_skipped(project, 'logging api is disabled')
    return

  # skip entire rule if dataflow API is disabled
  if not apis.is_enabled(context.project_id, 'dataflow'):
    report.add_skipped(project, 'dataflow api is disabled')
    return

  if (context.project_id in project_logs and
      project_logs[context.project_id].entries):
    failed_jobs = set()
    for log_entry in project_logs[context.project_id].entries:
      current_entry = get_path(log_entry, ('jsonPayload', 'message'), '')
      if log_entry['severity'] != 'WARNING' or not any(m not in current_entry
                                                       for m in MATCH_STRINGS):
        continue

      job_id = get_path(log_entry, ('resource', 'labels', 'job_id'))
      failed_jobs.add(job_id)

    if failed_jobs:
      extra_jobs = (f', and {len(failed_jobs) - MAX_JOBS_TO_DISPLAY} more jobs'
                    if len(failed_jobs) > MAX_JOBS_TO_DISPLAY else '')

      report.add_failed(
          project,
          f'{len(failed_jobs)} job(s) contain `Operation ongoing` or'
          ' `Processing Stuck` logs errors:'
          f" {', '.join(islice(failed_jobs, 20))} {extra_jobs}",
      )
    else:
      # only irrelevant logs were fetched
      report.add_ok(project)

  else:
    # no logs matched the filter
    report.add_ok(project)
