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
"""Cloud Composer has higher version than airflow-2.2.3

Airflow UI in Airflow 2.2.3 or earlier versions is vulnerable to CVE-2021-45229.
"Trigger DAG with config" screen was susceptible to XSS attacks through the
origin query argument. Highly recommened to upgrade to the latest Cloud Composer
version that supports Airflow 2.2.5.
"""

import re

from packaging import version

from gcpdiag import lint, models
from gcpdiag.queries import apis, composer


def run_rule(context: models.Context, report: lint.LintReportRuleInterface):
  if not apis.is_enabled(context.project_id, 'composer'):
    report.add_skipped(None, 'composer is disabled')
    return

  envs = composer.get_environments(context)

  if not envs:
    report.add_skipped(None, 'no Cloud Composer environments found')
    return

  xss_fixed_version = version.parse('2.2.5')
  pattern = re.compile(r'airflow-(.*)')

  for env in envs:
    airflow_version = pattern.search(env.image_version)
    if airflow_version and \
        version.parse(airflow_version.group(1)) < xss_fixed_version:
      report.add_failed(
          env, f'{env.name} image is {env.image_version}, which is vulnerable '
          'to XSS attack. Upgrade to the latest Cloud Composer version')
    else:
      report.add_ok(env)
