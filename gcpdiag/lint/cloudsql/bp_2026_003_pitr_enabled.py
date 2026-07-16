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
"""Cloud SQL instance has Point-in-Time Recovery (PITR) enabled

Point-in-Time Recovery (PITR) allows you to restore a Cloud SQL instance to a
specific point in time, providing protection against accidental data loss or
corruption. This rule checks if PITR is enabled.
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
        # Check if master has PITR enabled
        master_pitr_enabled = False
        if 'MYSQL' in master_instance.version:
          # MySQL requires both backups and bin log
          master_pitr_enabled = (
            master_instance.is_automated_backup_enabled and master_instance.is_binary_log_enabled
          )
        else:
          # Postgres/SQLServer require pointInTimeRecoveryEnabled
          master_pitr_enabled = master_instance.is_pitr_enabled

        if master_pitr_enabled:
          report.add_ok(instance, f'Replica of {master_name} which has PITR enabled')
        else:
          report.add_failed(instance, f'Replica of {master_name} which lacks PITR enabled')
      else:
        # Master not found in the list (could be cross-project or filtered out)
        # Note: Cross-project replicas will be skipped as we cannot verify the
        # master status across projects by default in the current context.
        report.add_skipped(
          instance, f'Replica of {master_name} (Master instance not found in current context)'
        )
      continue

    # This is a primary instance (or standalone)
    pitr_enabled = False
    if 'MYSQL' in instance.version:
      # For MySQL, check both backups and binaryLogEnabled
      pitr_enabled = instance.is_automated_backup_enabled and instance.is_binary_log_enabled
    else:
      # For PostgreSQL and SQL Server, check pointInTimeRecoveryEnabled
      pitr_enabled = instance.is_pitr_enabled

    if not pitr_enabled:
      report.add_failed(instance)
    else:
      report.add_ok(instance)
