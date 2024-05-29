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
"""Cloud Composer task isn't failing intermittently during scheduling

The user may encounter an error caused by multiple reasons like intermittent
task failures during scheduling, hit the dag parsing timeout,
unhandled exception, dynamic DAG generation or Out of Memory.

To minimize the impact of such errors, it is recommended to check the
common issues from our public documentation and follow the best practices.
"""

from boltons.iterutils import get_path

from gcpdiag import lint, models
from gcpdiag.queries import apis, composer, crm, logs

MATCH_STRING = (
    '[queued]> finished (failed) although the task says its queued. ' +
    '(Info: None) Was the task killed externally?')

FILTER = ['severity=ERROR', f'textPayload:("{MATCH_STRING}")']

logs_by_project = {}
envs_by_project = {}


def find_env(arr_of_composer_envs: list, search_str: str):
  """Compares the environment name from the error log with the list of composer environment objects

  Args:
    arr_of_composer_envs: list of composer environment objects
    search_str: string containing the name of composer search_str extracted from
      the error log

  Returns:
    environment: composer environment object
  """

  for environment in arr_of_composer_envs:
    if environment.name == search_str:
      return environment


def get_dag_task(error_message: str):
  """Extracts the airflow dag and task name from the error log message

  Args:
    error_message: string containing the error log message

  Returns:
    dag, task: airflow dag name and airflow task name
  """

  parts = error_message.split()
  start_index = None

  try:
    start_index = parts.index('<TaskInstance:') + 1
    full_task_name = parts[start_index]
    dag, task = full_task_name.split('.', 1)
    return dag, task
  except ValueError:
    return full_task_name, ''


def prefetch_rule(context: models.Context):
  envs_by_project[context.project_id] = composer.get_environments(context)


def prepare_rule(context: models.Context):
  logs_by_project[context.project_id] = logs.query(
      project_id=context.project_id,
      resource_type='cloud_composer_environment',
      log_name='log_id("airflow-scheduler")',
      filter_str=' AND '.join(FILTER),
  )


def run_rule(context: models.Context, report: lint.LintReportRuleInterface):
  project = crm.get_project(context.project_id)
  if not apis.is_enabled(context.project_id, 'logging'):
    report.add_skipped(None, 'cloud logging api is disabled')
    return

  if not apis.is_enabled(context.project_id, 'composer'):
    report.add_skipped(None, 'cloud composer api is disabled')
    return

  if context.project_id in logs_by_project:
    logs_ = logs_by_project.get(context.project_id)
    if logs_:
      dag_task_list = set()
      env_list = envs_by_project[context.project_id]

      for log_entry in logs_.entries:
        if log_entry['severity'] != 'ERROR' or MATCH_STRING not in get_path(
            log_entry, 'textPayload', default=''):
          continue

        error_message = get_path(log_entry, 'textPayload')

        dag_name, task_name = get_dag_task(error_message)

        environment = get_path(log_entry, ('resource', 'labels'))

        environment_detials = find_env(env_list,
                                       environment['environment_name'])

        if (dag_name, task_name, environment_detials) not in dag_task_list:
          report.add_failed(
              environment_detials,
              f'Task "{dag_name}/{task_name}" is failing intermittently',
          )
          dag_task_list.add((dag_name, task_name, environment_detials))

      return

  report.add_ok(project)
