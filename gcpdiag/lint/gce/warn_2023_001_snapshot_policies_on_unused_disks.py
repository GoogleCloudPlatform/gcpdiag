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
"""
GCE snapshot policies are defined only for used disks.

GCE scheduled snapshot policies are defined only for used disks,
Unused disks should be backed up using manual snapshots.
"""

from gcpdiag import lint, models
from gcpdiag.queries import crm, gce


def run_rule(context: models.Context, report: lint.LintReportRuleInterface):
  disks = gce.get_all_disks(context)

  if not disks:
    report.add_skipped(None, 'no disks found')
    return
  rule_ok = True
  for d in sorted(disks, key=lambda d: d.full_path):
    if d.has_snapshot_schedule and not d.in_use:
      report.add_failed(d)
      rule_ok = False
  if rule_ok:
    project = crm.get_project(context.project_id)
    report.add_ok(project)
