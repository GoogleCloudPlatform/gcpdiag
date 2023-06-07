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
"""Cloud Composer tasks are not failed due to resource pressure

During execution of a task, Airflow worker's subprocess responsible for Airflow
task execution could be interrupted abruptly due to resource pressure. In this
case, the task would be failed without emitting logs.
"""
from boltons.iterutils import get_path

from gcpdiag import lint, models
from gcpdiag.queries import apis, composer, logs

MATCH_STR = 'Celery command failed on host'
LOG_FILTER = ['severity=ERROR', f'textPayload:"{MATCH_STR}"']
logs_by_project = {}


def prepare_rule(context: models.Context):
  logs_by_project[context.project_id] = logs.query(
      project_id=context.project_id,
      resource_type='cloud_composer_environment',
      log_name='log_id("airflow-worker")',
      filter_str=' AND '.join(LOG_FILTER))


def run_rule(context: models.Context, report: lint.LintReportRuleInterface):
  if not apis.is_enabled(context.project_id, 'composer'):
    report.add_skipped(None, 'composer is disabled')
    return

  if not apis.is_enabled(context.project_id, 'logging'):
    report.add_skipped(None, 'logging api is disabled')
    return

  envs = composer.get_environments(context)

  if not envs:
    report.add_skipped(None, 'no Cloud Composer environments found')
    return

  resource_pressure_envs = set()

  if logs_by_project.get(context.project_id) and \
     logs_by_project[context.project_id].entries:
    for log_entry in logs_by_project[context.project_id].entries:
      # Filter out non-relevant log entries.
      if log_entry['severity'] != 'ERROR' or \
          MATCH_STR not in log_entry.get('textPayload', ''):
        continue

      env_name = get_path(log_entry, ('resource', 'labels', 'environment_name'))
      resource_pressure_envs.add(env_name)

  for env in envs:
    if env.name in resource_pressure_envs:
      report.add_failed(env)
    else:
      report.add_ok(env)
