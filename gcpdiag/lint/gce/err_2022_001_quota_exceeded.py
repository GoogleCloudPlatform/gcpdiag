# Copyright 2022 Google LLC
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
"""Project limits were not exceeded.

Cloud Monitoring will record the event when any service in your project is
reporting a quota exceeded error.

Rule will start failing if there is any quota exceeded event during the given
timeframe.
"""

from typing import Dict

from gcpdiag import config, lint, models
from gcpdiag.queries import crm, monitoring, quotas

_query_results_per_project_id: Dict[str, monitoring.TimeSeriesCollection] = {}


def prefetch_rule(context: models.Context):

  params = {'within_days': config.get('within_days')}
  _query_results_per_project_id[context.project_id] = \
      monitoring.query(
          context.project_id,
          quotas.QUOTA_EXCEEDED_QUERY_TEMPLATE.format_map(params))


def run_rule(context: models.Context, report: lint.LintReportRuleInterface):
  project = crm.get_project(context.project_id)

  if len(_query_results_per_project_id[context.project_id]) == 0:
    #no quota exceeded event during the period of time
    report.add_ok(project)
    return
  else:
    exceeded_quotas = []
    for i in _query_results_per_project_id[context.project_id].values():
      try:
        exceeded_quotas.append(i['labels']['metric.limit_name'])
      except KeyError:
        report.add_skipped(project, 'no data')
        #invalid query result
        return
    exceeded_quota_names = ', '.join(exceeded_quotas)
    report.add_failed(
        project,
        f'Project has recently exceeded the following quotas: {exceeded_quota_names}.'
    )
