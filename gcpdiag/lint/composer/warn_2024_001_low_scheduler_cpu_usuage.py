# Copyright 2024 Google LLC
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
"""Cloud Composer Scheduler CPU usage above 30%-35%.

Scheduler CPU usage is consistently below 30%-35%, Recommended to Reduce the
number of schedulers and Reduce the CPU of schedulers for Optimize environment
performance and costs
"""

from boltons.iterutils import get_path

from gcpdiag import lint, models
from gcpdiag.queries import apis, composer, monitoring

CPU_USAGE_THRESHOLD = 0.35

_query_results_per_project_id: dict[str, monitoring.TimeSeriesCollection] = {}
envs_by_project = {}


def prefetch_rule(context: models.Context):
  envs_by_project[context.project_id] = composer.get_environments(context)
  if not envs_by_project[context.project_id]:
    return

  _query_results_per_project_id[context.project_id] = monitoring.query(
      context.project_id,
      f"""
      fetch k8s_container
       | metric 'kubernetes.io/container/cpu/limit_utilization'
       | filter (resource.container_name == 'airflow-scheduler')
       | within 3d
       | group_by 3d, [value_limit_utilization: max(value.limit_utilization)]
       | filter val() <= {CPU_USAGE_THRESHOLD}
      """,
  )


def run_rule(context: models.Context, report: lint.LintReportRuleInterface):
  if not apis.is_enabled(context.project_id, 'composer'):
    report.add_skipped(None, 'composer is disabled')
    return

  envs = envs_by_project[context.project_id]

  if not envs:
    report.add_skipped(None, 'no Cloud Composer environments found')
    return

  under_usuage_envs = set()

  for ts in _query_results_per_project_id[context.project_id].values():
    try:
      env = get_path(ts, ('labels', 'resource.cluster_name'))
      under_usuage_envs.add(env)
    except KeyError:
      continue

  for env in envs:
    env_cluster_name = env.gke_cluster.split('/')[-1]
    if env_cluster_name in under_usuage_envs:
      report.add_failed(env, 'Scheduler CPU usage below 30-35%')
    else:
      report.add_ok(env)
