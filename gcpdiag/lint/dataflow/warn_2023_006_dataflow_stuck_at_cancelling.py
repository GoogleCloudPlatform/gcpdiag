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
"""A Dataflow job doesn't stuck in the cancelling state

A Dataflow job may get stuck in the cancelling state if
it is requested to cancel while a snapshot is in progress.
"""

import itertools

from gcpdiag import lint, models
from gcpdiag.queries import apis, crm, dataflow

dataflow_jobs_by_project = {}


def prefetch_rule(context: models.Context):
  dataflow_jobs_by_project[context.project_id] = dataflow.get_all_dataflow_jobs(
      context)


def run_rule(context: models.Context, report: lint.LintReportRuleInterface):
  project = crm.get_project(context.project_id)

  if not apis.is_enabled(context.project_id, 'dataflow'):
    report.add_skipped(project, 'dataflow api is disabled')
    return

  jobs = dataflow_jobs_by_project[context.project_id]

  failed_jobs = set()

  if not jobs:
    report.add_skipped(None, 'no jobs found')

  for job in jobs:
    if job.state == 'JOB_STATE_CANCELLING':
      if job.minutes_in_current_state > 30:
        failed_jobs.add(job.id)

  if failed_jobs:
    report.add_failed(
        project,
        'Some Dataflow jobs stuck in the cancelling state for more than 30 minutes: '
        + ', '.join(itertools.islice(failed_jobs, 20)),
    )
  else:
    report.add_ok(project)
