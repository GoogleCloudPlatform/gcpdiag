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
"""Cloud Composer logging level is set to INFO

Logging level of Airflow may have been set to DEBUG for troubleshooting
purposes. However, it is highly recommended to revert the logging level
back to INFO after the troubleshooting is completed. Leaving the logging
level at DEBUG might increase costs associated with Cloud Storage. Logging
levels higher than INFO (WARNING, ERROR) could suppress logs that are useful
to troubleshooting, so it also not recommended.
"""

from gcpdiag import lint, models
from gcpdiag.queries import apis, composer


def _check_info_logging_level(config) -> bool:
  # logging section in airflow2, core section in airflow1
  return config.get('logging-logging_level', 'INFO') == 'INFO' or \
         config.get('core-logging_level', 'INFO') == 'INFO'


def run_rule(context: models.Context, report: lint.LintReportRuleInterface):
  if not apis.is_enabled(context.project_id, 'composer'):
    report.add_skipped(None, 'composer is disabled')
    return

  envs = composer.get_environments(context)

  if not envs:
    report.add_skipped(None, 'no Cloud Composer environments found')
    return

  for env in envs:
    if not _check_info_logging_level(env.airflow_config_overrides):
      report.add_failed(env)
    else:
      report.add_ok(env)
