# Copyright 2026 Google LLC
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
"""Cloud SQL instances should have a maintenance window configured.

Configure a maintenance window for Cloud SQL instances to control when
disruptive updates can occur.
"""

from gcpdiag import lint, models
from gcpdiag.queries import cloudsql

# Note: This rule extends bp_ext_2023_001_maint_window.py to consider HA/replica configurations.


def run_rule(context: models.Context, report: lint.LintReportRuleInterface):
  instances = cloudsql.get_instances(context)
  if not instances:
    report.add_skipped(None, 'no Cloud SQL instances found')
    return

  # Map instances by name for quick lookup of master instances
  instance_map = {inst.name: inst for inst in instances}

  for instance in instances:
    # has_maint_window returns 0 if no maintenance window is set (set to 'Any').
    # A non-zero value (1-7) indicates a specific day of the week is set.
    if instance.has_maint_window != 0:
      report.add_ok(instance)
      continue

    # Replicas inherit the maintenance window from their primary.
    # Check if this is a replica and if its primary has a window.
    master_name = instance.master_instance_name
    if master_name:
      # masterInstanceName might be 'project:name' or just 'name'.
      if ':' in master_name:
        parts = master_name.rsplit(':', 1)
        master_project = parts[0]
        short_master_name = parts[1]
        if master_project != instance.project_id:
          report.add_skipped(
            instance,
            'master instance not found in current context (cross-project verification is not supported)',
          )
          continue
      else:
        short_master_name = master_name

      if short_master_name not in instance_map:
        report.add_skipped(
          instance,
          'master instance not found in current context (cross-project verification is not supported)',
        )
        continue
      master = instance_map[short_master_name]
      # Replicas inherit maintenance window from master. Check if master has one.
      if master and master.has_maint_window != 0:
        report.add_ok(instance)
        continue

      report.add_failed(
        instance,
        f'Cloud SQL replica {instance.name} (edition: {instance.edition}) is defined '
        f'with Maintenance Window as Any because its primary ({short_master_name}) has no window configured',
      )
      continue

    report.add_failed(
      instance,
      f'{instance.name} (edition: {instance.edition}) is defined with Maintenance Window as Any',
    )
