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
"""Cloud Composer is consistently in healthy state

Cloud Composer runs a liveness DAG named airflow_monitoring, which runs on a
schedule and reports environment health. If the liveness DAG run finishes
successfully, the health status is True, which means healthy. Otherwise, the
health status is False. Note that the environment health could be intermittently
unhealthy due to events like scheduled maintenances. However, overall it should
be healthy.
"""
from boltons.iterutils import get_path

from gcpdiag import lint, models
from gcpdiag.queries import apis, composer, monitoring

_query_results_per_project_id: dict[str, monitoring.TimeSeriesCollection] = {}


def prefetch_rule(context: models.Context):
  _query_results_per_project_id[context.project_id] = monitoring.query(
      context.project_id, """
      fetch cloud_composer_environment
      | metric 'composer.googleapis.com/environment/healthy'
      | align fraction_true_aligner(30m)
      | within 6h
      | filter val() == 0
      """)


def run_rule(context: models.Context, report: lint.LintReportRuleInterface):
  if not apis.is_enabled(context.project_id, 'composer'):
    report.add_skipped(None, 'composer is disabled')
    return

  envs = composer.get_environments(context)
  if not envs:
    report.add_skipped(None, 'no Cloud Composer environments found')
    return

  unhealthy_envs = set()

  for ts in _query_results_per_project_id[context.project_id].values():
    try:
      unhealthy_envs.add(get_path(ts, ('labels', 'resource.environment_name')))
    except KeyError:
      continue

  for env in envs:
    if env.name in unhealthy_envs:
      report.add_failed(env)
    else:
      report.add_ok(env)
