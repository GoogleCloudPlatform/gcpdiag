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
"""Dataflow job does not have a hot key

A Dataflow job might have hot key which can limit the ability of Dataflow
to process elements in parallel, which increases execution time.
"""

import itertools
import re

from boltons.iterutils import get_path

from gcpdiag import lint, models
from gcpdiag.queries import apis, crm, logs

MATCH_STR1 = r'A hot key(\s' '.*' ')? was detected in step'
MATCH_STR2 = 'A hot key was detected'
contains_required_pattern1 = re.compile(MATCH_STR1)
contains_required_pattern2 = re.compile(MATCH_STR2)

# Criteria to filter for logs
LOG_FILTER = [
    'severity>=WARNING',
    f'textPayload=~"{MATCH_STR1}" OR "{MATCH_STR2}"',
]
logs_by_project = {}


def prepare_rule(context: models.Context):
  logs_by_project[context.project_id] = logs.query(
      project_id=context.project_id,
      resource_type='dataflow_step',
      log_name=('log_id("dataflow.googleapis.com/worker") OR'
                ' log_id("dataflow.googleapis.com/harness")'),
      filter_str=' AND '.join(LOG_FILTER),
  )


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

      msg = get_path(log_entry, 'textPayload', default='')

      contains_required1 = contains_required_pattern1.search(msg)
      contains_required2 = contains_required_pattern2.search(msg)

      if not (log_entry['severity'] >= 'WARNING' and
              (contains_required1 or contains_required2)):
        continue

      job_id = get_path(
          log_entry,
          ('resource', 'labels', 'job_id'),
      )

      failed_jobs.add(job_id)

    if failed_jobs:
      report.add_failed(
          project,
          'Some Dataflow jobs having hot key are: ' +
          ', '.join(itertools.islice(failed_jobs, 20)),
      )
    else:
      report.add_ok(project)
  else:
    report.add_ok(project)
