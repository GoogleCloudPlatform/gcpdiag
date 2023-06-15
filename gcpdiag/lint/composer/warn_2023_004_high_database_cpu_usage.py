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
"""Cloud Composer database CPU usage does not exceed 80%

Airflow database performance issues can lead to overall DAG execution issues.
If the database CPU usage exceeds 80% for more than a few percent of the total
time, the database is overloaded and requires scaling.
"""
from typing import Dict

from boltons.iterutils import get_path

from gcpdiag import lint, models
from gcpdiag.queries import apis, composer, monitoring

CPU_USAGE_THRESHOLD = 0.8

_query_results_per_project_id: Dict[str, monitoring.TimeSeriesCollection] = {}
envs_by_project = {}


def prefetch_rule(context: models.Context):
  envs_by_project[context.project_id] = composer.get_environments(context)
  if not envs_by_project[context.project_id]:
    return

  _query_results_per_project_id[context.project_id] = \
    monitoring.query(
      context.project_id,
      f"""
      fetch cloud_composer_environment
       | metric 'composer.googleapis.com/environment/database/cpu/utilization'
       | within 1h
       | filter val() >= {CPU_USAGE_THRESHOLD}
      """)


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
      env = get_path(ts, ('labels', 'resource.environment_name'))
      cpu_usage = ts['values'][0][0]
      overloaded_envs[env] = cpu_usage
    except KeyError:
      continue

  for env in envs:
    if env.name in overloaded_envs:
      report.add_failed(
          env,
          f'database CPU usage exceeded 80% ({overloaded_envs[env.name]:.2f})')
    else:
      report.add_ok(env)
