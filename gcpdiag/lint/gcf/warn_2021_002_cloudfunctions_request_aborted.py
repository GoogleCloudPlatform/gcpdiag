# Copyright 2021 Google LLC
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
"""Cloud Functions have no scale up issues.

Log entries with Cloud Functions having scale up issues have been found.
"""
from boltons.iterutils import get_path

from gcpdiag import lint, models
from gcpdiag.queries import gcf, logs

#pylint: disable=line-too-long

MATCH_STR = 'The request was aborted because there was no available instance.'

logs_by_project = {}


def prepare_rule(context: models.Context):
  logs_by_project[context.project_id] = logs.query(
      project_id=context.project_id,
      resource_type='cloud_function',
      log_name='log_id("cloudfunctions.googleapis.com/cloud-functions")',
      filter_str=f'textPayload:"{MATCH_STR}"')


def run_rule(context: models.Context, report: lint.LintReportRuleInterface):
  cloudfunctions = gcf.get_cloudfunctions(context)
  if not cloudfunctions:
    report.add_skipped(None, f'no functions found {context}')
    return

  failed_functions = set()

  for query in logs_by_project.values():
    for log_entry in query.entries:
      if MATCH_STR not in get_path(log_entry, ('textPayload'), default=''):
        continue
      function_name = get_path(log_entry,
                               ('resource', 'labels', 'function_name'),
                               default='')
      status = get_path(log_entry, ('httpRequest', 'status'), default=0)
      if status in [429, 500] and function_name:
        failed_functions.add(function_name)

  for _, cloudfunction in sorted(cloudfunctions.items()):
    if cloudfunction.name in failed_functions:
      report.add_failed(cloudfunction,
                        f'{cloudfunction.name} failed to scale up.')
    else:
      report.add_ok(cloudfunction)
