# Copyright 2025 Google LLC
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
""" GKE cluster complies with the serial port logging organization policy.

When the constraints/compute.disableSerialPortLogging policy is enabled,
GKE clusters must be created with logging disabled (serial-port-logging-enable: 'false'),
otherwise the creation of new nodes in Nodepool will fail.
"""

from typing import List

from gcpdiag import lint, models
from gcpdiag.queries import gke, orgpolicy


def get_non_compliant_pools(cluster: gke.Cluster) -> List[str]:
  """
        Checks if org serial port logging policy is enforced and if cluster complies with it.

        Args:
            cluster: The GKE cluster to check.

        Returns:
            List[str]: List of non-compliant nodepool names
        """
  # Get the policy constraint status
  constraint = orgpolicy.get_effective_org_policy(
      cluster.project_id, 'constraints/compute.disableSerialPortLogging')

  # If policy is not enforced, return None (no compliance check needed) and empty list
  if not isinstance(
      constraint,
      orgpolicy.BooleanPolicyConstraint) or not constraint.is_enforced():
    return []

  # Get cluster node pools
  return [
      nodepool.name
      for nodepool in cluster.nodepools
      if nodepool.config.has_serial_port_logging_enabled
  ]


def run_rule(context: models.Context, report: lint.LintReportRuleInterface):
  clusters = gke.get_clusters(context)
  if not clusters:
    report.add_skipped(None, 'No clusters found')
    return

  for cluster in clusters.values():
    # Skip Autopilot clusters as they are managed by Google
    if cluster.is_autopilot:
      report.add_skipped(
          cluster,
          'Skipping Autopilot cluster - serial port logging managed by Google')
      continue

    # find list of non compliant node pools.
    non_compliant_pools = get_non_compliant_pools(cluster)
    if not non_compliant_pools:
      report.add_ok(cluster)
    else:
      report.add_failed(cluster, (
          f'The following nodepools do not comply with the serial port logging org policy: {', \
          '.join(non_compliant_pools)}'))
