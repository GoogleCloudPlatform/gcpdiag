#
# Copyright 2022 Google LLC
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
"""BigQuery jobs are not failing due to results being larger than the maximum response size

Query results for SQL queries in BigQuery that generate excessively large results and don't
set a destination table fail with job error "responseTooLarge"
"""
from boltons.iterutils import get_path

from gcpdiag import lint, models
from gcpdiag.queries import apis, crm, logs

MATCH_STR = 'Response too large to return'

RESPONSE_TOO_LARGE = [
    'severity=ERROR',
    'protoPayload.@type="type.googleapis.com/google.cloud.audit.AuditLog"',
    f'protoPayload.status.message:("{MATCH_STR}")',
]
logs_by_project = {}


def prepare_rule(context: models.Context):
  logs_by_project[context.project_id] = logs.query(
      project_id=context.project_id,
      resource_type='bigquery_resource',
      log_name='log_id("cloudaudit.googleapis.com/data_access")',
      filter_str=' AND '.join(RESPONSE_TOO_LARGE))


def run_rule(context: models.Context, report: lint.LintReportRuleInterface):
  project = crm.get_project(context.project_id)
  # skip entire rule is logging disabled
  if not apis.is_enabled(context.project_id, 'logging'):
    report.add_skipped(project, 'Logging api is disabled')
    return
  if not apis.is_enabled(context.project_id, 'bigquery'):
    report.add_skipped(project, 'bigquery api is disabled')
    return
  if logs_by_project.get(context.project_id) and \
     logs_by_project[context.project_id].entries:
    for log_entry in logs_by_project[context.project_id].entries:
      project_ok_flag = True
      if MATCH_STR not in get_path(log_entry,
                                   ('protoPayload', 'status', 'message'),
                                   default=''):
        continue
      else:
        report.add_failed(
            project,
            'has BigQuery jobs failing because query results are larger than the '
            'maximum response size')
        project_ok_flag = False
        break
    if project_ok_flag:
      report.add_ok(project)
  else:
    report.add_ok(project)
