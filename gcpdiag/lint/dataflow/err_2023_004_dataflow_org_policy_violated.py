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
"""Dataflow job does not fail due to violating an organization policy constraint in project

A dataflow job might fail if there are constraints for any
(eg compute.vmExternalIpAccess, compute.requireShieldedVm etc.)
that might limit VM instance creation in their project
"""

import itertools
import re

from boltons.iterutils import get_path

from gcpdiag import lint, models
from gcpdiag.queries import apis, crm, logs

MATCH_STR = 'Constraint constraints/.* violated for project'
contains_required_pattern = re.compile(MATCH_STR)

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
      msg = get_path(log_entry, ('textPayload'), default='')

      contains_required = contains_required_pattern.search(msg)

      # Filter out non-relevant log entries.
      if not (log_entry['severity'] == 'ERROR' and contains_required):
        continue

      job_id = get_path(
          log_entry,
          ('resource', 'labels', 'job_id'),
      )

      failed_jobs.add(job_id)

    if failed_jobs:
      report.add_failed(
          project, 'Some Dataflow jobs are unable to start workers ' +
          'due to violating an organization policy constraint in project: ' +
          ', '.join(itertools.islice(failed_jobs, 20)))
    else:
      report.add_ok(project)
  else:
    report.add_ok(project)
