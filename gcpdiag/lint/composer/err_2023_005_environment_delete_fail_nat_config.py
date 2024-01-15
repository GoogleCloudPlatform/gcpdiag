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
"""Composer environment deletion not failed due to NAT configuration

Having Composer automatically create pods and services' secondary IP ranges and
then configuring Cloud NAT for the subnet and these ranges makes it so the
environment deletion will fail. Verify a Composer environment deletion attempt
failed due to a Cloud NAT configuration
"""
from boltons.iterutils import get_path

from gcpdiag import lint, models
from gcpdiag.queries import apis, composer, logs

MATCH_STR_1 = 'Google Compute Engine: The subnetwork resource'
MATCH_STR_2 = 'is already being used by'
MATCH_STR_3 = '-Nat'
MATCH_STR_4 = 'Composer Backend timed out'

MATCH_METHOD = 'google.cloud.orchestration.airflow.service.v1.Environments.DeleteEnvironment'
FILTER_1 = [
    'severity=ERROR',
    ('protoPayload.methodName="google.cloud.orchestration.airflow.service.'
     'v1.Environments.DeleteEnvironment"'),
    (f'protoPayload.status.message:(("{MATCH_STR_1}" AND "{MATCH_STR_2}" AND'
     f' "{MATCH_STR_3}") OR ("{MATCH_STR_4}"))'),
]

logs_by_project = {}
envs_by_project = {}


def prepare_rule(context: models.Context):
  envs_by_project[context.project_id] = composer.get_environments(context)
  logs_by_project[context.project_id] = logs.query(
      project_id=context.project_id,
      resource_type='cloud_composer_environment',
      log_name='log_id("cloudaudit.googleapis.com%2Factivity")',
      filter_str=' AND '.join(FILTER_1),
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

  env_name_set = set()

  if logs_by_project.get(context.project_id) and \
     logs_by_project[context.project_id].entries:
    for log_entry in logs_by_project[context.project_id].entries:
      # filter out non -relevant entries
      logging_check_path = get_path(log_entry,
                                    ('protoPayload', 'status', 'message'),
                                    default='')
      if (log_entry['severity'] != 'ERROR' or
          log_entry['protoPayload']['methodName'] != MATCH_METHOD or
          (((MATCH_STR_1 not in logging_check_path) or
            (MATCH_STR_2 not in logging_check_path) or
            (MATCH_STR_3 not in logging_check_path)) and
           (MATCH_STR_4 not in logging_check_path))):
        continue
      env_name = get_path(log_entry, ('resource', 'labels', 'environment_name'))
      env_name_set.add(env_name)

  for env in envs:
    if (env.state == 'ERROR') and (env.name in env_name_set):
      report.add_failed(env)
    else:
      report.add_ok(env)
