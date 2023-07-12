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
"""Dataflow worker logs are not Throttled

Check that worker logs are not throttled in Dataflow jobs.
"""

from boltons.iterutils import get_path

from gcpdiag import lint, models
from gcpdiag.queries import apis, crm
from gcpdiag.queries.logs_helper import Equals, LogsQuery, REFound

logs_by_project = {}


def prepare_rule(context: models.Context):
  logs_by_project[context.project_id] = LogsQuery(
      project_id=context.project_id,
      resource_type='dataflow_step',
      log_name='log_id("dataflow.googleapis.com/worker")',
      search_exprs=[
          Equals(field='severity', value='WARNING'),
          REFound(
              field='jsonPayload.message',
              re_exp='Throttling logger worker',
          )
      ])
  logs_by_project[context.project_id].mk_query()


def run_rule(context: models.Context, report: lint.LintReportRuleInterface):
  project = crm.get_project(context.project_id)

  # skip entire rule if Logging or Dataflow API is disabled
  if not apis.is_enabled(context.project_id, 'logging'):
    report.add_skipped(project, 'logging api is disabled')
    return

  if not apis.is_enabled(context.project_id, 'dataflow'):
    report.add_skipped(project, 'dataflow api is disabled')
    return

  logs_query = logs_by_project[context.project_id]

  if logs_query.has_matching_entries:
    unique_jobs = logs_query.get_unique(lambda e: get_path(
        e, ('resource', 'labels', 'job_name'), default='unknown job'))
    report.add_failed(project,
                      f'Dataflow worker logs are throttled: {unique_jobs}')
  else:
    report.add_ok(project)
