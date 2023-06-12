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
"""Cloud Composer Scheduler CPU limit exceeded.

Airflow scheduler's CPU and memory metrics help you check whether the
scheduler's performance is a bottleneck in the overall Airflow performance.
"""

from boltons.iterutils import get_path

from gcpdiag import lint, models
from gcpdiag.queries import apis, composer, monitoring

CPU_USAGE_THRESHOLD = 1

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
       | within 1h
       | filter val() >= {CPU_USAGE_THRESHOLD}
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

  overloaded_envs = {}

  for ts in _query_results_per_project_id[context.project_id].values():
    try:
      env = get_path(ts, ('labels', 'resource.container_name'))
      cpu_usage = ts['values'][0][0]
      overloaded_envs[env] = cpu_usage
    except KeyError:
      continue

  for env in envs:
    if env.name in overloaded_envs:
      report.add_failed(
          env, f'Scheduler CPU limit exceeded({overloaded_envs[env.name]:.2f})')
    else:
      report.add_ok(env)
