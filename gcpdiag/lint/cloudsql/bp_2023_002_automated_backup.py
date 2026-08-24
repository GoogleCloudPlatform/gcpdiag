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

# Lint as: python3
"""Cloud SQL is configured with automated backup

Backups help you restore lost data to your Cloud SQL instance. Additionally,
if an instance is having a problem, you can restore it to a previous state by
using the backup to overwrite it. Enable automated backups for any instance that
contains necessary data. Backups protect your data from loss or damage.
"""

from gcpdiag import lint, models
from gcpdiag.queries import apis, cloudsql

instances_by_project = {}


def prefetch_rule(context: models.Context):
  instances_by_project[context.project_id] = cloudsql.get_instances(context)


def run_rule(context: models.Context, report: lint.LintReportRuleInterface):
  if not apis.is_enabled(context.project_id, 'sqladmin'):
    report.add_skipped(None, 'sqladmin is disabled')
    return

  instances = instances_by_project[context.project_id]

  if not instances:
    report.add_skipped(None, 'no CloudSQL instances found')
    return

  # Build a map for quick lookup
  instance_map = {instance.name: instance for instance in instances}

  for instance in instances:
    master_instance_full_name = instance.master_instance_name

    if master_instance_full_name:
      # This is a replica
      master_name = master_instance_full_name.split(':')[-1]
      master_instance = instance_map.get(master_name)

      if master_instance:
        # Check if master has automated backup enabled
        if master_instance.is_automated_backup_enabled:
          report.add_ok(instance, f'Replica of {master_name} which has automated backup enabled')
        else:
          report.add_failed(
            instance, f'Replica of {master_name} which lacks automated backup enabled'
          )
      else:
        report.add_skipped(
          instance, f'Replica of {master_name} (Master instance not found in current context)'
        )
      continue

    # This is a primary instance (or standalone)
    if not instance.is_automated_backup_enabled:
      report.add_failed(instance)
    else:
      report.add_ok(instance)
