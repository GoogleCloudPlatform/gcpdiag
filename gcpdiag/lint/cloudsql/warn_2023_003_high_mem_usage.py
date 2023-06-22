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
"""Cloud SQL instance's memory usage does not exceed 90%

If you have less than 10% memory in database/memory/components.cache and
database/memory/components.free combined, the risk of an OOM event is high.
"""
from typing import Dict

from boltons.iterutils import get_path

from gcpdiag import config, lint, models
from gcpdiag.queries import apis, cloudsql, monitoring

MEM_USAGE_THRESHOLD = 90  # 0 ~ 100 scale

_query_results_per_project_id: Dict[str, monitoring.TimeSeriesCollection] = {}
instances_by_project = {}


def prefetch_rule(context: models.Context):
  instances_by_project[context.project_id] = cloudsql.get_instances(context)

  if not instances_by_project[context.project_id]:
    return

  within_str = 'within %dd, d\'%s\'' % (config.get('within_days'),
                                        monitoring.period_aligned_now(60))

  _query_results_per_project_id[context.project_id] = \
    monitoring.query(
      context.project_id,
      f"""
      fetch cloudsql_database
       | metric 'cloudsql.googleapis.com/database/memory/components'
       | group_by 6h, [value_components_aggregate: aggregate(value.components)]
       | filter metric.component = 'Usage'
       | every 6h
       | filter val() >= {MEM_USAGE_THRESHOLD}
       | {within_str}
      """)


def run_rule(context: models.Context, report: lint.LintReportRuleInterface):
  if not apis.is_enabled(context.project_id, 'sqladmin'):
    report.add_skipped(None, 'sqladmin is disabled')
    return

  instances = instances_by_project[context.project_id]

  if not instances:
    report.add_skipped(None, 'no CloudSQL instances found')
    return

  overloaded_instances = set()

  for ts in _query_results_per_project_id[context.project_id].values():
    try:
      # project_id:instance_name
      full_name = get_path(ts, ('labels', 'resource.database_id'))
      overloaded_instances.add(full_name.split(':')[1])
    except (KeyError, IndexError):
      continue

  for instance in instances:
    if instance.name in overloaded_instances:
      report.add_failed(instance)
    else:
      report.add_ok(instance)
