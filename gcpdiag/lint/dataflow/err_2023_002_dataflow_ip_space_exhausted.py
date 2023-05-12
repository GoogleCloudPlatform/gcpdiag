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
"""Dataflow job does not fail during execution due to IP space exhaustion

A dataflow job runs successfully if subnet has enough ip space for all workers in job,
otherwise it fails with IP_SPACE_EXHAUSTED error.
"""

import itertools

from boltons.iterutils import get_path

from gcpdiag import lint, models
from gcpdiag.queries import apis, crm, logs

MATCH_STR = 'IP_SPACE_EXHAUSTED'

# Criteria to filter for logs
LOG_FILTER = ['severity=ERROR', f'textPayload=~"{MATCH_STR}"']
logs_by_project = {}


def prepare_rule(context: models.Context):
  logs_by_project[context.project_id] = logs.query(
      project_id=context.project_id,
      resource_type='dataflow_step',
      log_name='log_id("dataflow.googleapis.com/job-message")',
      filter_str=' AND '.join(LOG_FILTER))


def run_rule(context: models.Context, report: lint.LintReportRuleInterface):
  project = crm.get_project(context.project_id)

  # skip entire rule is logging disabled
  if not apis.is_enabled(context.project_id, 'logging'):
    report.add_skipped(project, 'logging api is disabled')
    return

  if not apis.is_enabled(context.project_id, 'dataflow'):
    report.add_skipped(project, 'dataflow api is disabled')
    return

  if (logs_by_project.get(context.project_id) and
      logs_by_project[context.project_id].entries):
    failed_jobs = set()
    for log_entry in logs_by_project[context.project_id].entries:
      # Filter out non-relevant log entries.
      if log_entry['severity'] != 'ERROR' or \
        MATCH_STR not in get_path(log_entry,
                     ('textPayload'), default=''):
        continue

      job_id = get_path(
          log_entry,
          ('resource', 'labels', 'job_id'),
      )

      failed_jobs.add(job_id)

    report.add_failed(
        project, 'Some Dataflow jobs failed due to exhaustion of IP Space: ' +
        ', '.join(itertools.islice(failed_jobs, 20)))
    return

  # in case of there is no log or all logs are non-relevant
  report.add_ok(project)
