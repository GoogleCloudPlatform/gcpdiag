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
"""GCE boot disk auto-delete is enabled.

When a VM instance is deleted, the boot disk should typically be deleted as well
to avoid orphaned disks that continue to incur storage costs. If auto-delete is
disabled on the boot disk, the disk will remain after the VM is deleted, which
may lead to unexpected costs and resource cleanup issues.

This rule checks that boot disks have auto-delete enabled. Exceptions may apply
for instances where boot disk preservation is intentionally configured for
backup or recovery purposes.
"""

import operator as op

from gcpdiag import lint, models
from gcpdiag.queries import gce


def run_rule(context: models.Context, report: lint.LintReportRuleInterface):
  instances = gce.get_instances(context)

  if not instances:
    report.add_skipped(None, 'no instances found')
    return

  for instance in sorted(instances.values(),
                         key=op.attrgetter('project_id', 'full_path')):
    # Skip GKE nodes as they are managed by GKE
    if instance.is_gke_node():
      report.add_skipped(instance, 'GKE node - managed by GKE')
      continue

    # Skip Dataproc instances as they are managed by Dataproc
    if instance.is_dataproc_instance():
      report.add_skipped(instance, 'Dataproc instance - managed by Dataproc')
      continue

    # Check boot disk auto-delete setting
    boot_disk_auto_delete = None
    boot_disk_name = None

    for disk in instance.disks:
      if disk.get('boot', False):
        boot_disk_auto_delete = disk.get('autoDelete', True)
        # Extract disk name from source URL
        source = disk.get('source', '')
        if source:
          boot_disk_name = source.split('/')[-1]
        else:
          boot_disk_name = disk.get('deviceName', 'unknown')
        break

    if boot_disk_auto_delete is None:
      report.add_skipped(instance, 'no boot disk found')
    elif boot_disk_auto_delete:
      report.add_ok(instance)
    else:
      report.add_failed(
          instance, f'Boot disk "{boot_disk_name}" has auto-delete disabled. '
          'This may lead to orphaned disks and unexpected costs when the VM is deleted.'
      )
