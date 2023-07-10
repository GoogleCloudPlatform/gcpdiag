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
"""Dataflow job doen't stuck at draining state for more than 3 hours

A Dataflow job might got stuck at draining as
draining doesn't fix stuck pipelines.
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
    if job.state == 'JOB_STATE_DRAINING':
      if job.minutes_in_current_state > 180:
        failed_jobs.add(job.id)
      else:
        continue
    else:
      continue

  if failed_jobs:
    report.add_failed(
        project,
        'Some Dataflow jobs stuck in draining for more than 3 hours are: ' +
        ', '.join(itertools.islice(failed_jobs, 20)),
    )
  else:
    report.add_ok(project)
