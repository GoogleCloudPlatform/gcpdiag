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
"""Cloud Composer Airflow Worker Pods not in Eviction state.

Pod eviction can happen when a particular pod in your environment's cluster
reaches its resource limits.If an Airflow worker pod is evicted, all task
instances running on that pod are interrupted, and later marked as failed by
Airflow.
"""

from boltons.iterutils import get_path

from gcpdiag import lint, models
from gcpdiag.queries import apis, composer, monitoring

_query_results_per_project_id: dict[str, monitoring.TimeSeriesCollection] = {}
envs_by_project = {}


def prefetch_rule(context: models.Context):
  envs_by_project[context.project_id] = composer.get_environments(context)
  if not envs_by_project[context.project_id]:
    return

  _query_results_per_project_id[context.project_id] = monitoring.query(
      context.project_id,
      """
       fetch cloud_composer_environment
       | metric 'composer.googleapis.com/environment/worker/pod_eviction_count'
       | within 6h
       | align delta(1m)
       | every 1m
       | filter val() > 0
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

  pod_evicted_envs = set()

  for ts in _query_results_per_project_id[context.project_id].values():
    try:
      env = get_path(ts, ('labels', 'resource.environment_name'))
      pod_evicted_envs.add(env)
    except KeyError:
      continue

  for env in envs:
    if env.name in pod_evicted_envs:
      report.add_failed(env, 'Airflow Worker Pod(s) evicted')
    else:
      report.add_ok(env)
