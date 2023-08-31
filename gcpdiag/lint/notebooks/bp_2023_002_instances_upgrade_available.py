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
"""Vertex AI Workbench user-managed notebook instances are up to date

Vertex AI Workbench user-managed notebook instance can be upgraded to have
latest bug fixes, new capabilities, framework and package updates
"""

from gcpdiag import lint, models
from gcpdiag.queries import apis, notebooks

instances_by_project = {}


def prefetch_rule(context: models.Context):
  instances_by_project[context.project_id] = notebooks.get_instances(context)


def run_rule(context: models.Context, report: lint.LintReportRuleInterface):

  if not apis.is_enabled(context.project_id, 'notebooks'):
    report.add_skipped(None, 'Notebooks API is disabled')
    return

  instances = instances_by_project[context.project_id]

  if not instances:
    report.add_skipped(None, 'No instances found')
    return

  for instance in instances.values():
    is_upgradeable = notebooks.instance_is_upgradeable(context, instance.name)
    upgradeable_message = (
        'Instance is upgradeable - '
        f'upgradeVersion: "{is_upgradeable.get("upgradeVersion", "unknown")}", '
        f'upgradeInfo: "{is_upgradeable.get("upgradeInfo", "unknown")}", '
        f'upgradeImage: {is_upgradeable.get("upgradeImage", "unknown")}')
    if is_upgradeable.get('upgradeable', False):
      report.add_failed(instance, upgradeable_message)
    else:
      report.add_ok(instance)
