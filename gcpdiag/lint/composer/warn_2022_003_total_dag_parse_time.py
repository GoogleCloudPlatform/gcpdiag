#
# Copyright 2021 Google LLC
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

# Lint as: python3
"""Composer scheduler parses all DAG files without overloading

If the total DAG parse time exceeds about 10 seconds, the schedulers might
be overloaded with DAG parsing and cannot run DAGs effectively.
"""

from typing import Dict

from gcpdiag import config, lint, models
from gcpdiag.queries import apis, composer, crm, monitoring

TOTAL_DAG_PARSE_SECONDS = 10

_query_results_per_project_id: Dict[str, monitoring.TimeSeriesCollection] = {}


def prefetch_rule(context: models.Context):
  composer_environments = composer.get_environments(context)
  if not composer_environments:
    return

  within_str = 'within %dd, d\'%s\'' % (config.get('within_days'),
                                        monitoring.period_aligned_now(60))
  _query_results_per_project_id[context.project_id] = \
    monitoring.query(
      context.project_id,
      # maximum total DAG parse time during config.get('within_days')
      f"""
      fetch cloud_composer_environment
      | metric 'composer.googleapis.com/environment/dag_processing/total_parse_time'
      | {within_str}
      | every 1m
      | group_by {config.get('within_days')}d,
                [value_total_parse_time_max: max(value.total_parse_time)]
      """)


def run_rule(context: models.Context, report: lint.LintReportRuleInterface):
  project = crm.get_project(context.project_id)
  if not apis.is_enabled(context.project_id, 'composer'):
    report.add_skipped(None, 'composer is disabled')
    return

  composer_environments = composer.get_environments(context)
  if not composer_environments:
    report.add_skipped(project, 'no environments found')
    return

  metric_values = {}
  for query_result in \
  _query_results_per_project_id[context.project_id].values():
    try:
      metric_values[query_result['labels']['resource.environment_name']] = \
      query_result['values'][0][0]
    except KeyError:
      continue

  for environment in composer_environments:
    try:
      if metric_values[environment.name] >= TOTAL_DAG_PARSE_SECONDS:
        report.add_failed(
            environment,
            f'max total DAG parse time: {metric_values[environment.name]:.2f} seconds'
        )
      else:
        report.add_ok(environment)
    except KeyError:
      report.add_skipped(environment, 'no metrics')
