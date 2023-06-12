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
"""Airflow schedulers are healthy for the last hour

Airflow schedulers report heartbeat signals every predefined interval called
scheduler_heartbeat_sec (default: 5 seconds). If any heartbeats are received
within the threshold time (default: 30 seconds), the Scheduler heartbeat from
the monitoring dashboard is marked as Green, which means healthy. Otherwise the
status is unhealthy. Note that if your environment has more than one scheduler,
then the status is healthy as long as at least one of schedulers is responding.
"""
from typing import Dict

from boltons.iterutils import get_path

from gcpdiag import lint, models
from gcpdiag.queries import apis, composer, monitoring

_query_results_per_project_id: Dict[str, monitoring.TimeSeriesCollection] = {}
envs_by_project = {}


def prefetch_rule(context: models.Context):
  envs_by_project[context.project_id] = composer.get_environments(context)
  if not envs_by_project[context.project_id]:
    return

  _query_results_per_project_id[context.project_id] = \
    monitoring.query(
      context.project_id,
      """
      fetch cloud_composer_environment
      | metric 'composer.googleapis.com/environment/scheduler_heartbeat_count'
      | group_by 1m,
          [value_scheduler_heartbeat_count_mean:
             mean(value.scheduler_heartbeat_count)]
      | every 1m
      | within 1h
      | filter val() == 0
      """)


def run_rule(context: models.Context, report: lint.LintReportRuleInterface):
  if not apis.is_enabled(context.project_id, 'composer'):
    report.add_skipped(None, 'composer is disabled')
    return

  envs = envs_by_project[context.project_id]

  if not envs:
    report.add_skipped(None, 'no Cloud Composer environments found')
    return

  unhealthy_schedulers_envs = set()

  for ts in _query_results_per_project_id[context.project_id].values():
    try:
      unhealthy_schedulers_envs.add(
          get_path(ts, ('labels', 'resource.environment_name')))
    except KeyError:
      continue

  for env in envs:
    if env.name in unhealthy_schedulers_envs:
      report.add_failed(env)
    else:
      report.add_ok(env)
