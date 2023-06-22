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
"""Cloud Composer does not override the StatsD configurations

Metrics from Cloud Composer like scheduler heartbeat, number of completed tasks
and pods are collected via the StatsD daemon. If you override the default StatsD
configuration, it will cause missing metrics in the monitoring pages and
components including airflow-scheduler that depend on Statsd metrics for
healthcheck will be marked as unhealthy.
"""

from gcpdiag import lint, models
from gcpdiag.queries import apis, composer

envs_by_project = {}


def prefetch_rule(context: models.Context):
  envs_by_project[context.project_id] = composer.get_environments(context)


def run_rule(context: models.Context, report: lint.LintReportRuleInterface):
  if not apis.is_enabled(context.project_id, 'composer'):
    report.add_skipped(None, 'composer is disabled')
    return

  envs = envs_by_project[context.project_id]

  if not envs:
    report.add_skipped(None, 'no Cloud Composer environments found')
    return

  for env in envs:
    if any(
        key.startswith('metrics-statsd_')
        for key in env.airflow_config_overrides.keys()):
      report.add_failed(env)
    else:
      report.add_ok(env)
