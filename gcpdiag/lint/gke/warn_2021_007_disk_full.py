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
"""GKE nodes have enough free space on the boot disk.

GKE nodes need free space on their boot disks to be able to function properly.
If /var is getting full, it might be because logs are not being rotated
correctly, or maybe a container is creating too much data in the overlayfs.
"""

from collections import defaultdict
from typing import Dict, List, Set

from gcpdiag import lint, models
from gcpdiag.queries import gke, monitoring

# Verify that free/(free + used) is above this threshold
MIN_FREE_THRESHOLD = 0.05

_query_results_per_project_id: Dict[str, monitoring.TimeSeriesCollection] = {}


def prefetch_rule(context: models.Context):
  # Fetch the metrics for all nodes.
  #
  # Note: we only group_by instance_id because of performance reasons (it gets
  # much slower if you group_by multiple labels)
  clusters = gke.get_clusters(context)
  if not clusters:
    return

  # Only check the latest usage values
  within_str = 'within 5m, d\'%s\'' % (monitoring.period_aligned_now(300))
  _query_results_per_project_id[context.project_id] = monitoring.query(
      context.project_id, f"""
  fetch gce_instance
  | metric 'compute.googleapis.com/guest/disk/bytes_used'
  | filter metric.device_name == 'sda1'
  | {within_str}
  | next_older 5m
  | filter_ratio_by [resource.instance_id], metric.state == 'free'
  | every 5m
  """)


def run_rule(context: models.Context, report: lint.LintReportRuleInterface):
  clusters = gke.get_clusters(context)
  if not clusters:
    report.add_skipped(None, 'no clusters found')
    return

  # Organize data per-cluster.
  clusters_with_data: Set[gke.Cluster] = set()
  bad_nodes_per_cluster: Dict[gke.Cluster, List[gke.Node]] = defaultdict(list)
  for ts in _query_results_per_project_id[context.project_id].values():
    try:
      instance_id = ts['labels']['resource.instance_id']
      node = gke.get_node_by_instance_id(context, instance_id)
      cluster = node.nodepool.cluster
      clusters_with_data.add(cluster)
      value = ts['values'][0][0]
      if value < MIN_FREE_THRESHOLD:
        bad_nodes_per_cluster[cluster].append(node)
    except KeyError:
      continue

  # Go over all selected clusters and report results.
  for _, c in sorted(clusters.items()):
    if c not in clusters_with_data:
      report.add_skipped(c, 'no data')
    elif c not in bad_nodes_per_cluster:
      report.add_ok(c)
    else:
      report.add_failed(
          c,
          'nodes found founds with boot disk free space less than %d%%:\n. ' %
          (MIN_FREE_THRESHOLD * 100) + '\n. '.join(
              [node.instance.name for node in bad_nodes_per_cluster[c]]))
