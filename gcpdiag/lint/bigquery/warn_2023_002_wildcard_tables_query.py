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
"""No errors querying wildcard tables

A query has been used on a wildcard table and the field was not found
"""
from boltons.iterutils import get_path

from gcpdiag import lint, models
from gcpdiag.queries import apis, crm, logs

#String the is unique to this error
MATCH_STR = 'Unrecognized name:'

#Where to look for the error
ERROR_IN_LOGGING = [
    'severity=ERROR',
    'protoPayload.@type="type.googleapis.com/google.cloud.audit.AuditLog"',
    r'protoPayload.serviceData.jobCompletedEvent.job.jobStatistics.referencedTables.tableId=~"\*$"',
    f'protoPayload.serviceData.jobCompletedEvent.job.jobStatus.error.message:"{MATCH_STR}"'
]
logs_by_project = {}


#Get the logs for the error
def prepare_rule(context: models.Context):
  logs_by_project[context.project_id] = logs.query(
      project_id=context.project_id,
      resource_type='bigquery_resource',
      log_name='log_id("cloudaudit.googleapis.com%2Fdata_access")',
      filter_str=' AND '.join(ERROR_IN_LOGGING))


def run_rule(context: models.Context, report: lint.LintReportRuleInterface):
  project = crm.get_project(context.project_id)
  # skip entire rule is logging disabled
  if not apis.is_enabled(context.project_id, 'logging'):
    report.add_skipped(project, 'Logging api is disabled')
    return
  # skip the rule if bigquery is not enabled
  if not apis.is_enabled(context.project_id, 'bigquery'):
    report.add_skipped(project, 'bigquery api is disabled')
    return
  #list of all found errors
  error_entries = []

  #loop through the errors
  if logs_by_project.get(context.project_id) and \
     logs_by_project[context.project_id].entries:
    for log_entry in logs_by_project[context.project_id].entries:
      #make sure we found the correct errors
      if MATCH_STR not in get_path(log_entry,
                                   ('protoPayload', 'status', 'message'),
                                   default=''):
        continue
      else:
        #add the error to the error list
        error_entries.append(log_entry['protoPayload']['status']['message'])

    #if there are no errors, report success
    if len(error_entries) == 0:
      report.add_ok(project)
    #if there are more than 10 errors, report failure
    elif len(error_entries) >= 1:
      report.add_failed(
          project,
          ('There have been errors in your project'
           ' where a field was not found in a query using a wildcard table'),
          '  to prevent this, please rewrite your query or change the tables schema'
      )
  else:
    report.add_ok(project)
