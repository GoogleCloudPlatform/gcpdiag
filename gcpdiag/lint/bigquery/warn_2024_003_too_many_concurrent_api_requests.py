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
"""BigQuery job does not fail due to Maximum API requests per user per method exceeded.

BigQuery returns Quota exceeded or Exceeded rate limits error when you hit the
rate limit for the number of API requests to a BigQuery API per user per method.
"""

from boltons.iterutils import get_path

from gcpdiag import lint, models
from gcpdiag.queries import apis, crm, logs

MATCH_STR = 'too many API requests per user per method for this user_method'

TOO_MANY_API_REQUESTS_FILTER = [
    'severity=ERROR',
    f'protoPayload.status.message =~ ("{MATCH_STR}")',
]

logs_by_project = {}


def prepare_rule(context: models.Context):
  logs_by_project[context.project_id] = logs.query(
      project_id=context.project_id,
      resource_type='bigquery_resource',
      log_name='log_id("cloudaudit.googleapis.com/activity")',
      filter_str=' AND '.join(TOO_MANY_API_REQUESTS_FILTER),
  )


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
      method_name = get_path(log_entry, ('protoPayload', 'methodName'))
      report.add_failed(
          project,
          f'BigQuery user_method ({method_name}) exceeded quota for concurrent'
          ' api requests per user per method',
      )
      return

  # in case of there is no log or all logs are non-relevant
  report.add_ok(project)
