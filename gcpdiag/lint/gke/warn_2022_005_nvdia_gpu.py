# Copyright 2022 Google LLC
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
"""NVIDIA GPU device drivers are installed on GKE nodes with GPU

After adding GPU nodes to the GKE cluster, the NVIDIA's device drivers
should be installed in the nodes. Google provides a DaemonSet that will
install the drivers.
"""

from typing import Dict

from gcpdiag import lint, models
from gcpdiag.queries import gke, monitoring

_query_results_per_project_id: Dict[str, monitoring.TimeSeriesCollection] = {}


def prefetch_rule(context: models.Context):
  clusters = gke.get_clusters(context)
  if not clusters:
    return

  # Fetch the metrics for all clusters.
  _query_results_per_project_id[context.project_id] = \
      monitoring.query(
          context.project_id, """
fetch k8s_container
| metric 'kubernetes.io/container/uptime'
| filter (metadata.user.c'k8s-app' = "nvidia-driver-installer")
| within 1h
| group_by [resource.project_id,
    cluster_name: resource.cluster_name,
    location: resource.location,
    container_image: metadata.system_labels.container_image]
  """)


def run_rule(context: models.Context, report: lint.LintReportRuleInterface):
  clusters = gke.get_clusters(context)
  if not clusters:
    report.add_skipped(None, 'no clusters found')
    return

  # Skip GKE cluster without GPU
  check_clusters = []
  for _, cluster in sorted(clusters.items()):
    if not cluster.has_monitoring_enabled():
      report.add_skipped(cluster, 'monitoring disabled')
      continue
    if not cluster.nodepools:
      report.add_skipped(None, 'no nodepools found')
      continue
    for nodepool in cluster.nodepools:
      if nodepool.config.has_accelerators() and nodepool.node_count > 0:
        check_clusters.append(cluster)
        break
      else:
        report.add_skipped(nodepool, 'no nodes with GPU found')

  if len(check_clusters) == 0:
    return

  # Organize the metrics per-cluster.
  per_cluster_results: Dict[tuple, Dict[str, str]] = {}
  for ts in _query_results_per_project_id[context.project_id].values():
    try:
      cluster_key = (ts['labels']['resource.project_id'],
                     ts['labels']['location'], ts['labels']['cluster_name'])
      per_cluster_results.setdefault(cluster_key, {})
    except KeyError:
      # Ignore metrics that don't have those labels
      pass

  # Go over the list of reported clusters
  for c in check_clusters:
    ts_cluster_key = (c.project_id, c.location, c.name)
    if ts_cluster_key in per_cluster_results:
      report.add_ok(c)
      return
    else:
      report.add_failed(
          c,
          'The DaemonSet of nvidia-driver-installer is not found in the GKE cluster.'
      )
