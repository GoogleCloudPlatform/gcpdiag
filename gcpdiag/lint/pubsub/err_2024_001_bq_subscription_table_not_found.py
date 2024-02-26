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
"""Pub/Sub Bigquery Subscription Created using Exist BigQuery table.

Unable to Create the BigQuery Subscription using  BigQuery table does not
already exist, Check If the table you are trying to use for Bigquery
Subscription creation  is already existed in the BigQuery or not.
"""

from boltons.iterutils import get_path

from gcpdiag import lint, models
from gcpdiag.queries import apis, crm, logs

MATCH_STR = 'Not found: Table'

TABLE_EXIST_CHECK_FILTER = [
    'severity=ERROR',
    f'protoPayload.status.message:"{MATCH_STR}"',
]

logs_by_project = {}


def prepare_rule(context: models.Context):
  logs_by_project[context.project_id] = logs.query(
      project_id=context.project_id,
      resource_type='pubsub_subscription',
      log_name='log_id("cloudaudit.googleapis.com/activity")',
      filter_str=' AND '.join(TABLE_EXIST_CHECK_FILTER))


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
      report.add_failed(
          project,
          'The BigQuery "' +
          log_entry['protoPayload']['request']['bigqueryConfig']['table'] +
          '" table does not already exist, which is required for '
          'setting up a BigQuery subscription.',
      )
      return

  # in case of there is no log or all logs are non-relevant
  report.add_ok(project)
