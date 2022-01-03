# Copyright 2021 Google LLC
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
"""Secure Boot is enabled

Google recommends enabling Secure Boot if you can ensure that it doesn't
prevent a representative test VM from booting and if it is appropriate
for your workload. Compute Engine does not enable Secure Boot by default
because unsigned drivers and other low-level software might not be compatible.

https://cloud.google.com/compute/shielded-vm/docs/shielded-vm
"""
import operator as op

from gcpdiag import lint, models
from gcpdiag.queries import gce


def run_rule(context: models.Context, report: lint.LintReportRuleInterface):
  instances = gce.get_instances(context)
  instances_count = 0
  for i in sorted(instances.values(), key=op.attrgetter('project_id', 'name')):
    # GKE nodes are not checked by this rule
    if i.is_gke_node():
      continue
    instances_count += 1
    if i.secure_boot_enabled():
      report.add_ok(i)
    else:
      report.add_failed(
          i,
          'it is recommended to enable Secure Boot if it is appropriate for your workload'
      )
  if not instances_count:
    report.add_skipped(None, 'no instances found')
