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
"""Cloud SQL instance's avg CPU utilization is not over 98% for 6 hours

If CPU utilization is over 98% for six hours, your instance is not properly
sized for your workload, and it is not covered by the SLA.
"""
from typing import Dict

from boltons.iterutils import get_path

from gcpdiag import lint, models
from gcpdiag.queries import apis, cloudsql, monitoring

CPU_USAGE_THRESHOLD = 0.98

_query_results_per_project_id: Dict[str, monitoring.TimeSeriesCollection] = {}
instances_by_project = {}


def prefetch_rule(context: models.Context):
  instances_by_project[context.project_id] = cloudsql.get_instances(context)

  if not instances_by_project[context.project_id]:
    return

  _query_results_per_project_id[context.project_id] = \
    monitoring.query(
      context.project_id,
      f"""
      fetch cloudsql_database
       | metric 'cloudsql.googleapis.com/database/cpu/utilization'
       | group_by 6h, [value_utilization_mean: mean(value.utilization)]
       | every 5m
       | filter val() >= {CPU_USAGE_THRESHOLD}
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
