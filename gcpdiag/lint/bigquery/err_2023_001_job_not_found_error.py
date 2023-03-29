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
"""Jobs called via the API are all found

BigQuery jobs have been requested via the API and they have not been found,
this can be due to giving incorrect information in the call, such as jobID or location
"""
import itertools

from boltons.iterutils import get_path

from gcpdiag import lint, models
from gcpdiag.queries import apis, crm, logs

#String the is unique to this error
MATCH_STR = 'Not found: Job'

#Where to look for the error
JOB_NOT_FOUND = [
    'severity=ERROR',
    'protoPayload.@type="type.googleapis.com/google.cloud.audit.AuditLog"',
    'protoPayload.methodName="jobservice.getqueryresults"',
    f'protoPayload.status.message:("{MATCH_STR}")'
]
logs_by_project = {}


#Get the logs for the error
def prepare_rule(context: models.Context):
  logs_by_project[context.project_id] = logs.query(
      project_id=context.project_id,
      resource_type='bigquery_resource',
      log_name='log_id("cloudaudit.googleapis.com%2Fdata_access")',
      filter_str=' AND '.join(JOB_NOT_FOUND))


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
  error_entries = set()

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
        msg = log_entry['protoPayload']['status']['message']
        job_id = msg.replace('Not found: Job ', '')
        error_entries.add(job_id)

    error_msg = ', '.join(itertools.islice(error_entries, 10))
    if len(error_entries) > 10:
      error_msg += ', ...'
    #if there are no errors, report success
    if len(error_entries) == 0:
      report.add_ok(project)
    #if there are more than 10 errors, report failure
    else:
      #if there are errors, report them and what jobs had the error
      report.add_failed(
          project,
          'This happens when calls to the API to find a job, that comeback with no answers.',
          (' Make sure to provide the correct region in the API call.'
           f'There were {len(error_entries)} jobs not found: {error_msg}'))
  else:
    report.add_ok(project)
