# Copyright 2024 Google LLC
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

# Lint as: python3
"""Data Fusion version is supported.

A major or minor version of Cloud Data Fusion environment is supported for a
specific period of time after it is released.After that period, instances that
continue to use the environment version are no longer supported.
"""

from datetime import datetime

from packaging import version

from gcpdiag import lint, models
from gcpdiag.queries import apis, crm, datafusion

projects_instances = {}


def prefetch_rule(context: models.Context):
  projects_instances[context.project_id] = datafusion.get_instances(context)


def run_rule(context: models.Context, report: lint.LintReportRuleInterface):
  """Checks if the datafusion version is supported.

  Args:
    context: The context for the rule, containing the project_id.
    report: The report to which to report results.
  """
  version_policy = datafusion.extract_support_datafusion_version()

  if not version_policy:
    report.add_skipped(None, 'No Supported Versions Data Obtained')
    return

  if not apis.is_enabled(context.project_id, 'datafusion'):
    report.add_skipped(
        None,
        'Cloud Data Fusion API is not enabled in'
        f' {crm.get_project(context.project_id)}',
    )
    return

  datafusion_instances = projects_instances[context.project_id]
  if not datafusion_instances:
    report.add_skipped(None,
                       f'Cloud Data Fusion instances were not found {context}')
    return

  current_date = datetime.now().strftime('%Y-%m-%d')

  for datafusion_instance in sorted(datafusion_instances.values()):

    df_instance_parsed_version = version.parse(str(datafusion_instance.version))

    version_to_compare = (
        f'{df_instance_parsed_version.major}.{df_instance_parsed_version.minor}'
    )

    if version_to_compare in version_policy:
      if current_date <= version_policy[version_to_compare]:
        report.add_ok(
            datafusion_instance,
            f'\n\tDatafusion Version: {datafusion_instance.version}'
            f'\n\tSupports till {version_policy[version_to_compare]}',
        )
      else:
        report.add_failed(
            datafusion_instance,
            '\n\tDatafusion Version:'
            f' {datafusion_instance.version}\n\tSupported till'
            f' {version_policy[version_to_compare]}(Upgrade DataFusion'
            ' Environment)',
        )
