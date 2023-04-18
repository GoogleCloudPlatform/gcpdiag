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
"""GKE pod CIDR range utilization close to 100%.

The maximum amount of nodes in a GKE cluster is limited based on its pod CIDR
range. This test checks if any of the pod CIDRs in use in the cluster has 80%
or more utilization. Note, this is limited to a single cluster although the pod
CIDR can be shared across clusters.
Enable the network management API to see GKE IP address utilization insights
in Network Analyzer.
"""
from typing import Dict, List, Tuple

from gcpdiag import lint, models
from gcpdiag.queries import gke

#Test fails if pod cidr usage is above FAIL_THRESHOLD (.8 similar to GKE IP utilization insights)
FAIL_THRESHOLD_RATIO = .8
MAX_NODEPOOLS_TO_REPORT = 10


def nodepool_calc(cluster) -> Tuple[dict, dict]:
  """Calculates the number of used ips per pod cidr range
   and the number of nodes in each node pool"""

  cidr_used_ips: Dict[str, int] = {}
  nodepools_by_range: Dict[str, List[str]] = {}
  nodepool_nodes: Dict[str, int] = {}

  for np in cluster.nodepools:

    pod_range = np.pod_ipv4_cidr_block

    migs = np.instance_groups
    total_nodes = 0
    for mig in migs:
      # approximation assuming that only running instances actually use pod cidr ranges
      nodes = mig.count_no_action_instances()
      total_nodes += nodes

    nodepool_nodes[np.name] = total_nodes

    if pod_range not in cidr_used_ips:

      cidr_used_ips[pod_range] = 0
      nodepools_by_range[pod_range] = []

    #sum up used IPs per pod range - running nodes*pod ip addresses allocated per node
    cidr_used_ips[pod_range] = cidr_used_ips[pod_range] + (
        total_nodes * (2**(32 - np.pod_ipv4_cidr_size)))

    nodepools_by_range[pod_range].append(np.name)

  return cidr_used_ips, nodepools_by_range


def run_rule(context: models.Context, report: lint.LintReportRuleInterface):
  clusters = gke.get_clusters(context)
  if not clusters:
    report.add_skipped(None, 'no clusters found')
  for _, cluster in sorted(clusters.items()):

    if cluster.is_vpc_native:
      cidr_used_ips, nodepools_by_range = nodepool_calc(cluster)

      high_use = False
      summary = ''

      for pod_range, ips in cidr_used_ips.items():

        used_ips = ips
        total_ip_addresses = pod_range.num_addresses

        nodepools = nodepools_by_range[pod_range]

        threshold_ips_used = total_ip_addresses * FAIL_THRESHOLD_RATIO

        if used_ips > threshold_ips_used:
          high_use = True

          if summary:
            summary += '\n'

          summary += (
              f'{pod_range}({round(used_ips/total_ip_addresses*100)}% IPs used): '
              f'{",".join(nodepools[:MAX_NODEPOOLS_TO_REPORT])}')

          if len(nodepools) > MAX_NODEPOOLS_TO_REPORT:
            summary += f' ({len(nodepools) - MAX_NODEPOOLS_TO_REPORT} more node pool(s))'

      if high_use:
        report.add_failed(cluster, summary)
      else:
        report.add_ok(cluster)

    else:
      #route-based: https://cloud.google.com/kubernetes-engine/docs/how-to/routes-based-cluster

      size = cluster.current_node_count
      pod_range = cluster.pod_ipv4_cidr
      #4096 IPs reserved for services range
      total_ip_addresses = pod_range.num_addresses - 4096

      #256 because each node is assigned /24 from the pod CIDR range
      used_ips = (size * 256)

      threshold_ips_used = (total_ip_addresses) * FAIL_THRESHOLD_RATIO

      if used_ips > threshold_ips_used:
        report.add_failed(
            cluster,
            f'{pod_range}({round(used_ips/total_ip_addresses*100)}% IPs used): all node pools'
        )
      else:
        report.add_ok(cluster)
