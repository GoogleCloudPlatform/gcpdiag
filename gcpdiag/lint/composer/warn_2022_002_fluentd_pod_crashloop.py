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
"""fluentd pods in Composer enviroments are not crashing

The fluentd runs as a daemonset and collects logs from all environment
components and uploads the logs to Cloud Logging. All fluentd pods in an
environment could be stuck in a CrashLoopBackOff state after upgrading the
enviromennt and no logs appear in the Cloud Logging.
"""
from boltons.iterutils import get_path

from gcpdiag import lint, models
from gcpdiag.queries import apis, composer, crm, logs

MATCH_STR = 'unexpected error error_class=NoMethodError'
MATCH_STR2 = "undefined method `subscription' for nil:NilClass"
POD_NAME = 'composer-builder-fluentd'

LOG_FILTER = [
    'severity=INFO',
    f'labels.k8s-pod/name="{POD_NAME}"',
    f'textPayload:"{MATCH_STR}"',
    f'textPayload:"{MATCH_STR2}"',
]

logs_by_project = {}


def prepare_rule(context: models.Context):
  logs_by_project[context.project_id] = logs.query(
      project_id=context.project_id,
      resource_type='k8s_container',
      log_name='log_id("stdout")',
      filter_str=' AND '.join(LOG_FILTER))


def run_rule(context: models.Context, report: lint.LintReportRuleInterface):
  project = crm.get_project(context.project_id)

  # skip entire rule is logging disabled
  if not apis.is_enabled(context.project_id, 'logging'):
    report.add_skipped(project, 'logging api is disabled')
    return

  envs = composer.get_environments(context)
  name_to_env = {env.name: env for env in envs}

  if not envs:
    report.add_skipped(project, 'no envs found')
    return

  stuck_in_crashloop_envs = []

  if logs_by_project.get(context.project_id) and \
     logs_by_project[context.project_id].entries:
    for log_entry in logs_by_project[context.project_id].entries:
      # Filter out non-relevant log entries.
      if log_entry['severity'] != 'INFO' or \
         POD_NAME != get_path(log_entry,
                     ('labels', 'k8s-pod/name'), default='') or \
         MATCH_STR not in log_entry.get('textPayload', '') or \
         MATCH_STR2 not in log_entry.get('textPayload', ''):
        continue

      # region-name-suffix-gke format (us-east4-composer-stg-v2-a106130c-gke)
      cluster_name = get_path(log_entry, ('resource', 'labels', 'cluster_name'),
                              default='')

      env_name = '-'.join(cluster_name.split('-')[2:-2])
      if env_name and env_name not in stuck_in_crashloop_envs:
        stuck_in_crashloop_envs.append(env_name)

  for env_name in stuck_in_crashloop_envs:
    report.add_failed(name_to_env[env_name],
                      'has fluentd pods stuck in the crashloop')

  for env_name in [
      env_name for env_name in name_to_env
      if env_name not in stuck_in_crashloop_envs
  ]:
    report.add_ok(name_to_env[env_name])
