# Copyright 2026 Google LLC
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
"""Cloud SQL replica instances do not have high replication lag

Cloud SQL read replicas with high replication lag might serve stale data or
stop replicating from the primary database. Ensure the replica has sufficient
resources to keep up with the workload.
"""

from typing import Dict, Iterable, Set

from gcpdiag import lint, models, utils
from gcpdiag.queries import apis, cloudsql, monitoring

REPLICA_LAG_THRESHOLD_SECONDS = 600
_query_results_per_project_id: Dict[str, monitoring.TimeSeriesCollection] = {}
instances_by_project: Dict[str, Iterable[cloudsql.Instance]] = {}


def prefetch_rule(context: models.Context):
  if not apis.is_enabled(context.project_id, 'sqladmin'):
    return

  instances_by_project[context.project_id] = cloudsql.get_instances(context)

  if not instances_by_project[context.project_id]:
    return

  replicas = [
    inst for inst in instances_by_project[context.project_id] if inst.master_instance_name
  ]
  if not replicas:
    return

  try:
    _query_results_per_project_id[context.project_id] = monitoring.query(
      context.project_id,
      f"""
        fetch cloudsql_database
         | metric 'cloudsql.googleapis.com/database/replication/replica_lag'
         | within 14d
         | group_by 5m, [value_replica_lag_mean: mean(value.replica_lag)]
         | every 5m
         | filter val() > {REPLICA_LAG_THRESHOLD_SECONDS}
        """,
    )
  except utils.GcpApiError:
    pass


def run_rule(context: models.Context, report: lint.LintReportRuleInterface):
  if not apis.is_enabled(context.project_id, 'sqladmin'):
    report.add_skipped(None, 'sqladmin is disabled')
    return

  instances = instances_by_project.get(context.project_id)

  if not instances:
    report.add_skipped(None, 'no CloudSQL instances found')
    return

  replicas = [inst for inst in instances if inst.master_instance_name]
  if not replicas:
    report.add_skipped(None, 'no CloudSQL replicas found')
    return

  lagging_instances: Set[str] = set()

  # If the monitoring query was executed and returned results, parse them
  query_results = _query_results_per_project_id.get(context.project_id)
  if query_results:
    for ts in query_results.values():
      try:
        # database_id is in format project_id:instance_name
        labels = ts.get('labels', {}) if isinstance(ts, dict) else {}
        database_id = labels.get('resource.database_id', '')
        if database_id:
          instance_name = database_id.split(':')[-1]
          lagging_instances.add(instance_name)
      except (KeyError, IndexError):
        continue

  for instance in replicas:
    if instance.name in lagging_instances:
      report.add_failed(
        instance,
        reason=(
          f'Cloud SQL replica instance {instance.name} has a replication'
          f' lag exceeding {REPLICA_LAG_THRESHOLD_SECONDS} seconds.'
        ),
      )
    else:
      report.add_ok(instance)
