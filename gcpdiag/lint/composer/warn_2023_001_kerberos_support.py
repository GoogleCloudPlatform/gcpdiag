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
"""Cloud Composer does not override Kerberos configurations

Cloud Composer does not support Airflow Kerberos configuration yet.
"""

from gcpdiag import lint, models
from gcpdiag.queries import apis, composer


def _check_kerberos_overrides(config) -> bool:
  return config.get('core-security', '') == 'kerberos' or \
     any(key.startswith('kerberos-') for key in config.keys())


def run_rule(context: models.Context, report: lint.LintReportRuleInterface):
  if not apis.is_enabled(context.project_id, 'composer'):
    report.add_skipped(None, 'composer is disabled')
    return

  envs = composer.get_environments(context)

  if not envs:
    report.add_skipped(None, 'no Cloud Composer environments found')
    return

  for env in envs:
    if _check_kerberos_overrides(env.airflow_config_overrides):
      report.add_failed(
          env,
          'has Airflow kerberos configurations, which is not supported yet.')
    else:
      report.add_ok(env)
