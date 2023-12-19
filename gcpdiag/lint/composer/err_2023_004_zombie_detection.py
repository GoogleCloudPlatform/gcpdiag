# Copyright 2023 Google LLC
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
"""Cloud Composer Dags are not getting zombie error

Based on heartbeat, the Airflow scheduler is able to detect abnormally
terminated tasks - if they're missing for extended period of time, a task will
be detected as a zombie and the similar message will be written in logs.
"""
from boltons.iterutils import get_path

from gcpdiag import lint, models
from gcpdiag.queries import apis, composer, logs

MATCH_STR = 'Detected zombie job'
LOG_FILTER = ['severity=ERROR', f'textPayload:"{MATCH_STR}"']
logs_by_project = {}
envs_by_project = {}


def prefetch_rule(context: models.Context):
  envs_by_project[context.project_id] = composer.get_environments(context)


def prepare_rule(context: models.Context):
  logs_by_project[context.project_id] = logs.query(
      project_id=context.project_id,
      resource_type='cloud_composer_environment',
      log_name='log_id("airflow-scheduler")',
      filter_str=' AND '.join(LOG_FILTER),
  )


def run_rule(context: models.Context, report: lint.LintReportRuleInterface):
  if not apis.is_enabled(context.project_id, 'composer'):
    report.add_skipped(None, 'composer is disabled')
    return

  if not apis.is_enabled(context.project_id, 'logging'):
    report.add_skipped(None, 'logging api is disabled')
    return

  envs = envs_by_project[context.project_id]

  if not envs:
    report.add_skipped(None, 'no Cloud Composer environments found')
    return

  sigkilled_envs = set()

  if (logs_by_project.get(context.project_id) and
      logs_by_project[context.project_id].entries):
    for log_entry in logs_by_project[context.project_id].entries:
      # Filter out non-relevant log entries.
      if log_entry['severity'] != 'ERROR' or MATCH_STR not in log_entry.get(
          'textPayload', ''):
        continue

      env_name = get_path(log_entry, ('resource', 'labels', 'environment_name'))
      sigkilled_envs.add(env_name)

  for env in envs:
    if env.name in sigkilled_envs:
      report.add_failed(env)
    else:
      report.add_ok(env)
