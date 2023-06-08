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
"""Vertex AI Workbench instance is in healty boot disk space status

The boot disk space status is unhealthy if the disk space is greater than 85%
full.
"""
from gcpdiag import lint, models
from gcpdiag.queries import apis, notebooks


def run_rule(context: models.Context, report: lint.LintReportRuleInterface):

  if not apis.is_enabled(context.project_id, 'notebooks'):
    report.add_skipped(None, 'Notebooks API is disabled')
    return

  instances = notebooks.get_instances(context)
  if not instances:
    report.add_skipped(None, 'No instances found')
    return

  for instance in instances.values():
    health_info = notebooks.get_instance_health_info(context, instance.name)

    if not health_info:
      report.add_skipped(instance, 'No health info found')
      continue

    disk_util = int(health_info.get('boot_disk_utilization_percent', '0'))

    if disk_util > 85:
      report.add_failed(instance)
    else:
      report.add_ok(instance)
