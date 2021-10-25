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
"""Istio/ASM version not deprecated nor close to deprecation in GKE

As of GKE 1.22, all Istio versions below 1.10.0 and ASM versions of 1.10.2 and
below will no longer work. It is recommended that you upgrade to ASM Managed
Control Plane or Istio version 1.10.3+ to avoid outages.
"""

from typing import Dict

from gcpdiag import lint, models
from gcpdiag.queries import gke, monitoring
from gcpdiag.queries.gke import Version

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
| filter (metadata.system_labels.container_image =~ '.*pilot.*')
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

  # Skip querying metrics if no cluster is in 1.21+
  check_clusters = []
  for _, c in sorted(clusters.items()):
    current_version = c.master_version
    if Version('1.21') < current_version < Version('1.23'):
      check_clusters.append(c)
    else:
      report.add_ok(c, f'GKE {c.master_version}')

  if len(check_clusters) == 0:
    return

  # Organize the metrics per-cluster.
  per_cluster_results: Dict[tuple, Dict[str, str]] = {}
  for ts in _query_results_per_project_id[context.project_id].values():
    try:
      cluster_key = (ts['labels']['resource.project_id'],
                     ts['labels']['location'], ts['labels']['cluster_name'])
      cluster_values = per_cluster_results.setdefault(cluster_key, {})
      cluster_values['container_image'] = ts['labels']['container_image']
    except KeyError:
      # Ignore metrics that don't have those labels
      pass

  # Go over the list of reported clusters
  for c in check_clusters:
    ts_cluster_key = (c.project_id, c.location, c.name)
    if ts_cluster_key not in per_cluster_results:
      report.add_skipped(c, 'no Istio/ASM reported')
    else:
      container_image = per_cluster_results[ts_cluster_key]['container_image']
      (_, istio_version) = container_image.split(':')
      if Version(istio_version) > Version('1.10.2'):
        report.add_ok(c, f'Istio/ASM {istio_version}')
        return
      else:
        report.add_failed(
            c,
            f'Current GKE version: {c.master_version} (Release channel: '+\
            f'{c.release_channel})\nIn-cluster Istio/ASM control plane ' +\
            f'version: {istio_version}'
        )
