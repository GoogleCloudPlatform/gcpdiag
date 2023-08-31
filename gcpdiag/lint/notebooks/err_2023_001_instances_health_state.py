# Copyright 2023 Google LLC
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
"""Vertex AI Workbench user-managed notebook instances are healthy

Rule which verifies the Vertex AI Workbench user-managed notebook instances have
a healthy state
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
    if not instance.name:
      report.add_skipped(instance, 'Instance name not found')
      continue

    health_state = notebooks.get_instance_health_state(context, instance.name)
    health_state_message = f'Health state = {health_state}'
    if health_state == notebooks.HealthStateEnum.HEALTHY:
      report.add_ok(instance)
    if health_state == notebooks.HealthStateEnum.UNHEALTHY:
      report.add_failed(instance, health_state_message)
    else:
      report.add_skipped(instance, health_state_message)
