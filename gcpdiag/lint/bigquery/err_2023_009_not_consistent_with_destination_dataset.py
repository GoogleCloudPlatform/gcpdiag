# Copyright 2023 Google LLC
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
"""BigQuery job not failed due to Scheduled query with multiple DML

Destination/Target dataset can only be set up for scheduled queries with one
single DML statement. When two DML statements are present the second DML
statement will not pick up the correct destination/target dataset and will throw
an error.
"""

from boltons.iterutils import get_path

from gcpdiag import lint, models
from gcpdiag.queries import apis, crm, logs

MATCH_STR = (
    "Dataset specified in the query ('') is not consistent with Destination"
    ' dataset')

FILTER = [
    'severity=ERROR',
]

logs_by_project = {}


def prepare_rule(context: models.Context):
  logs_by_project[context.project_id] = logs.query(
      project_id=context.project_id,
      resource_type='bigquery_dts_config',
      log_name=(
          'log_id("bigquerydatatransfer.googleapis.com%2Ftransfer_config")'),
      filter_str=' AND '.join(FILTER),
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

  project_ok_flag = True
  config_id_set = set()

  if (logs_by_project.get(context.project_id) and
      logs_by_project[context.project_id].entries):
    #loop through the errors
    for log_entry in logs_by_project[context.project_id].entries:
      # Filter out non-relevant log entries.
      if MATCH_STR not in get_path(log_entry, ('jsonPayload', 'message'),
                                   default=''):
        continue

      config_id = get_path(log_entry, ('resource', 'labels', 'config_id'))
      if config_id not in config_id_set:
        report.add_failed(
            project,
            'Scheduled Query failed due to Scheduled query with multiple DML \n'
            + config_id)
        config_id_set.add(config_id)
        project_ok_flag = False

    if project_ok_flag:
      report.add_ok(project)
  else:
    report.add_ok(project)
