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
"""Snapshot should be created before it expires in less than 1hour of creation.

Unable to create snapshot if the subscription backlog is too old and message of
'subscription's backlog is too old' is displayed on the cloud console.
"""

from boltons.iterutils import get_path

from gcpdiag import lint, models
from gcpdiag.queries import apis, crm, logs

MATCH_STR = ('The operation could not be completed because the requested '
             'source subscription\'s backlog is too old')

SNAPSHOT_CREATION_FAIL_CHECK_FILTER = [
    'severity=ERROR',
    f'protoPayload.status.message:"{MATCH_STR}"',
]

logs_by_project = {}


def prepare_rule(context: models.Context):
  logs_by_project[context.project_id] = logs.query(
      project_id=context.project_id,
      resource_type='pubsub_snapshot',
      log_name='log_id("cloudaudit.googleapis.com/activity")',
      filter_str=' AND '.join(SNAPSHOT_CREATION_FAIL_CHECK_FILTER))


def run_rule(context: models.Context, report: lint.LintReportRuleInterface):
  project = crm.get_project(context.project_id)

  # skip entire rule is logging disabled
  if not apis.is_enabled(context.project_id, 'logging'):
    report.add_skipped(project, 'logging api is disabled')
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
          'The snapshot creation fails since backlog in subscription is greater than 6days23hours'
          + 'which makes it eligible to expire in 1hour after creation',
      )
      return

  # in case of there is no log or all logs are non-relevant
  report.add_ok(project)
