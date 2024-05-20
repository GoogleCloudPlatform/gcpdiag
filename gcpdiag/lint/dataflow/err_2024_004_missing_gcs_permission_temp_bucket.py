# Copyright 2024 Google LLC
#
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
"""The Dataflow job has the necessary GCS permissions for the temporary bucket.

Two primary reasons cause Dataflow jobs to fail when writing to a storage
bucket: either the specified bucket does not exist within the targeted Google
Cloud project, or the associated service account lacks the necessary permissions
to write to it.
"""

import re

from boltons.iterutils import get_path

from gcpdiag import lint, models
from gcpdiag.queries import apis, crm, logs

MATCH_STR = 'Failed to write a file to temp location'

# Criteria to filter for logs
LOG_FILTER = ['severity=ERROR', f'textPayload=~"{MATCH_STR}"']
logs_by_project = {}


def prepare_rule(context: models.Context):
  logs_by_project[context.project_id] = logs.query(
      project_id=context.project_id,
      resource_type='dataflow_step',
      log_name='log_id("dataflow.googleapis.com/job-message")',
      filter_str=' AND '.join(LOG_FILTER),
  )


def run_rule(context: models.Context, report: lint.LintReportRuleInterface):
  """Runs the rule and reports any failed checks.

  Args:
    context: Context of the rule.
    report: A report object to report fail findings.
  """
  project = crm.get_project(context.project_id)

  # skip entire rule if Logging or Dataflow API's are disabled
  if not apis.is_enabled(context.project_id, 'logging'):
    report.add_skipped(project, 'logging api is disabled')
    return

  if not apis.is_enabled(context.project_id, 'dataflow'):
    report.add_skipped(project, 'dataflow api is disabled')
    return

  project_ok_flag = True

  if logs_by_project.get(context.project_id) and \
     logs_by_project[context.project_id].entries:
    failed_jobs = set()
    for log_entry in logs_by_project[context.project_id].entries:
      # Filter out non-relevant log entries.
      if log_entry['severity'] != 'ERROR' or MATCH_STR not in get_path(
          log_entry, 'textPayload', default=''):
        continue

      project_ok_flag = False

      job_name = get_path(
          log_entry,
          ('resource', 'labels', 'job_name'),
      )

      message = get_path(log_entry, 'textPayload')
      bucket_name_pattern = r"'([^']+)'"
      match = re.search(bucket_name_pattern, message)
      bucket_name = None

      if match:
        bucket_name = match.group(1)

      if job_name not in failed_jobs:
        failed_jobs.add(job_name)
        report.add_failed(
            project,
            f'Check {bucket_name} bucket exists and\nCheck {job_name} Dataflow'
            ' job Missing GCS permissions for temp bucket',
        )

  if project_ok_flag:
    report.add_ok(project)
