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
"""GKE clusters must comply with serial port logging policy.

When the constraints/compute.disableSerialPortLogging policy is enabled,
GKE clusters must be created with logging disabled (serial-port-logging-enable: 'false'),
otherwise the creation will fail.
"""

from gcpdiag import lint, models
from gcpdiag.queries import gke

def run_rule(context: models.Context, report: lint.LintReportRuleInterface):
  clusters = gke.get_clusters(context)
  clusters_checked = 0

  for cluster in clusters.values():
    clusters_checked += 1

    try:
      # Skip Autopilot clusters as they are managed by Google
      if cluster.is_autopilot:
        report.add_skipped(
            cluster,
            'Skipping Autopilot cluster - serial port logging managed by Google'
        )
        continue

      # Check if cluster complies with serial port logging policy
      if cluster.is_serial_port_logging_compliant():
        report.add_ok(cluster)
      else:
        report.add_failed(
            cluster,
            msg=
            ('Cluster does not comply with serial port logging policy. '
             'When constraints/compute.disableSerialPortLogging is enabled, '
             'all node pools must have serial-port-logging-enable set to false'
            ),
            remediation=(
                'Update the node pool metadata to set '
                '"serial-port-logging-enable": "false" for all node pools'))

    except Exception as e:
      report.add_skipped(cluster, f'Error checking cluster: {str(e)}')

  if not clusters_checked:
    report.add_skipped(None, 'No clusters found')
