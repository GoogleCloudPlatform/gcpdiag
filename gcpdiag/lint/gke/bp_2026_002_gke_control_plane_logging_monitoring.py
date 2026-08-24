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
"""GKE control plane logging and monitoring enabled.

Control plane logging and monitoring (API_SERVER, SCHEDULER,
and CONTROLLER_MANAGER) are essential for troubleshooting
cluster-level issues and monitoring the health of the GKE
control plane.
"""

from gcpdiag import lint, models
from gcpdiag.queries import gke


def run_rule(context: models.Context, report: lint.LintReportRuleInterface):
  clusters = gke.get_clusters(context)
  if not clusters:
    report.add_skipped(None, 'no clusters found')
    return
  for _, c in sorted(clusters.items()):
    disabled: list[str] = []
    if not c.has_control_plane_logging_enabled():
      disabled.append('control plane logging')
    if not c.has_control_plane_monitoring_enabled():
      disabled.append('control plane monitoring')

    if disabled:
      report.add_failed(c, ' and '.join(disabled) + ' are disabled')
    else:
      report.add_ok(c)
