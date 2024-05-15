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
# pylint: disable=line-too-long
"""Dataflow and its controller service account have the necessary permissions to interact with Pub/Sub topics.

This rule ensures your Dataflow jobs have the `pubsub.subscriber` role to read messages,
and the controller service account has the `pubsub.topics.get` permission (typically included in `pubsub.viewer`)
to manage subscriptions. Without the correct permissions, Dataflow jobs will fail to create subscriptions,
resulting in `GETTING_PUBSUB_SUBSCRIPTION_FAILED` errors and disrupting your data pipelines.
"""

from boltons.iterutils import get_path

from gcpdiag import lint, models
from gcpdiag.queries import apis, crm, logs

MATCH_STR1 = ('GETTING_PUBSUB_SUBSCRIPTION_FAILED')
MATCH_STR2 = ('User not authorized to perform this action')

# Criteria to filter for logs
LOG_FILTER = [
    'severity>=WARNING', f'textPayload=~("{MATCH_STR1}" AND "{MATCH_STR2}")'
]
logs_by_project = {}


def prepare_rule(context: models.Context):
  logs_by_project[context.project_id] = logs.query(
      project_id=context.project_id,
      resource_type='dataflow_step',
      log_name='log_id("dataflow.googleapis.com/job-message")',
      filter_str=' AND '.join(LOG_FILTER),
  )


def run_rule(context: models.Context, report: lint.LintReportRuleInterface):
  """The method first checks if the Logging or Dataflow APIs are enabled for the project.

  If either API is disabled, the method skips the rule and returns.
  If both APIs are enabled, the method checks for the log entries in the project.
  If the log entries are found, the method reports the failed resources.

  Args:
    context: The context for the rule, including the project_id and other info.
    report: The report to which any failed resources will be added.
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

  if context.project_id in logs_by_project:
    failed_jobs = set()
    for log_entry in logs_by_project[context.project_id].entries:
      # Filter out non-relevant log entries.
      if log_entry['severity'] != 'WARNING' or MATCH_STR1 not in get_path(
          log_entry, 'textPayload', default=''):
        continue

      project_ok_flag = False

      job_id = get_path(
          log_entry,
          ('resource', 'labels', 'job_id'),
      )

      if job_id not in failed_jobs:
        failed_jobs.add(job_id)
        report.add_failed(
            project,
            f'Dataflow not creating Pub/Sub subscriptions for the job id:{job_id}'
        )

  if project_ok_flag:
    report.add_ok(project)
