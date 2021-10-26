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
"""GKE cluster size close to maximum allowed by pod range

The maximum amount of nodes in a GKE cluster is limited based on its pod CIDR
range. This test checks if the cluster is approaching the maximum amount of
nodes allowed by the pod range. Users may end up blocked in production if they
are not able to scale their cluster due to this hard limit imposed by the pod
CIDR.
"""

from gcpdiag import lint, models
from gcpdiag.queries import gke

#test will fail if node usage is above FAIL_THRSHOLD of the max allowed by the pod CIDR.
FAIL_THRESHOLD_RATIO = .9


def cluster_max_size(cluster) -> int:
  """Calculates max a mount of nodes based on cluster pod cidr
  """
  pod_range = cluster.pod_ipv4_cidr
  cluster_max_nodes = 1
  for np in cluster.nodepools:
    max_per_np = len(list(pod_range.subnets(new_prefix=np.pod_ipv4_cidr_size)))
    if max_per_np > cluster_max_nodes:
      cluster_max_nodes = max_per_np
  return cluster_max_nodes


def run_rule(context: models.Context, report: lint.LintReportRuleInterface):
  clusters = gke.get_clusters(context)
  if not clusters:
    report.add_skipped(None, 'no clusters found')
  for _, c in sorted(clusters.items()):
    size = c.current_node_count
    max_size = cluster_max_size(c)

    threshold_node_count = float(max_size) * FAIL_THRESHOLD_RATIO

    size_summary = f'{size}/{max_size} nodes used.'

    if size > threshold_node_count:
      report.add_failed(
          c, 'Pod CIDR: {}. Test threshold: {} ({}%).'.format(
              c.pod_ipv4_cidr, round(threshold_node_count),
              round(FAIL_THRESHOLD_RATIO * 100)), size_summary)
    else:
      report.add_ok(c, size_summary)
