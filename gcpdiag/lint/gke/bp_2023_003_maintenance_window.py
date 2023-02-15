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
"""GKE maintenance windows are defined

Maintenance windows give you fine-grained control over when automatic
maintenance can occur on GKE clusters. They allow administrators to
control the timing and impact of these updates, ensuring minimal disruption
to running workloads.
"""

from gcpdiag import lint, models
from gcpdiag.queries import gke

clusters_by_project = {}


def prepare_rule(context: models.Context):
  clusters_by_project[context.project_id] = gke.get_clusters(context)


def run_rule(context: models.Context, report: lint.LintReportRuleInterface):
  clusters = clusters_by_project[context.project_id]
  if not clusters:
    report.add_skipped(None, 'no clusters found')
  for _, c in sorted(clusters.items()):
    if not c.has_maintenance_window():
      report.add_failed(c, ' does not configure a maintenance window')
    else:
      report.add_ok(c)
