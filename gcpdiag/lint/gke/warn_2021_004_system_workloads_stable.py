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
"""GKE system workloads are running stable.

GKE includes some system workloads running in the user-managed nodes which are
essential for the correct operation of the cluster. We verify that restart count
of containers in one of the system namespaces (kube-system, istio-system,
custom-metrics) stayed stable in the last 24 hours.
"""

# To add to the online description of the rule:
#
# To find the pod names with the containers that are restarting, you can use this
# MQL query in Metrics explorer:
#
#     fetch k8s_container
#     | metric 'kubernetes.io/container/restart_count'
#     | filter (resource.namespace_name == 'kube-system' ||
#               resource.namespace_name == 'istio-system')
#     | align delta(1h)
#     | every 1h
#     | group_by [resource.pod_name], .sum
#     | filter val() > 0

from typing import Dict

from gcpdiag import config, lint, models
from gcpdiag.queries import gke, monitoring

# SLO: at least 99.8% of minutes are good (3 minutes in a day)
SLO_BAD_MINUTES = 3

_query_results_per_project_id: Dict[str,
                                    monitoring.TimeSeriesCollection] = dict()


def prefetch_rule(context: models.Context):
  clusters = gke.get_clusters(context)
  if not clusters:
    return

  # Fetch the metrics for all clusters.
  global _query_results_per_project_id
  within_str = 'within %dd, d\'%s\'' % (config.WITHIN_DAYS,
                                        monitoring.period_aligned_now(60))
  _query_results_per_project_id[context.project_id] = monitoring.query(
      context.project_id, f"""
fetch k8s_container
| metric 'kubernetes.io/container/restart_count'
| filter (resource.namespace_name == 'kube-system' ||
          resource.namespace_name == 'istio-system' ||
          resource.namespace_name == 'custom-metrics') &&
         metadata.system.top_level_controller_type != 'Node'
| {within_str}
| align delta(1m)
| filter val() >= 1
| group_by 1d, .count
| filter val() > {SLO_BAD_MINUTES}
| group_by [resource.project_id,
    cluster_name: resource.cluster_name,
    location: resource.location,
    controller: metadata.system.top_level_controller_name], [ .count ]
  """)


def run_rule(context: models.Context, report: lint.LintReportRuleInterface):
  clusters = gke.get_clusters(context)
  if not clusters:
    report.add_skipped(None, 'no clusters found')
    return

  # Organize the metrics per-cluster.
  per_cluster_results: Dict[tuple, Dict[str, int]] = dict()
  global _query_results_per_project_id
  for ts in _query_results_per_project_id[context.project_id].values():
    try:
      cluster_key = (ts['labels']['resource.project_id'],
                     ts['labels']['location'], ts['labels']['cluster_name'])
      cluster_values = per_cluster_results.setdefault(cluster_key, dict())
      cluster_values[ts['labels']['controller']] = ts
    except KeyError:
      # Ignore time series that don't have the required labels.
      pass

  # Go over the list of reported clusters
  for _, c in sorted(clusters.items()):
    ts_cluster_key = (c.project_id, c.location, c.name)
    if ts_cluster_key not in per_cluster_results:
      report.add_ok(c)
    else:
      report.add_failed(
          c, 'restarting: ' +
          ', '.join(per_cluster_results[ts_cluster_key].keys()))
