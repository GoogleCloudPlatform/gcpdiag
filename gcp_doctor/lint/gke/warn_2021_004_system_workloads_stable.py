# Lint as: python3
"""GKE system workloads are running stable.

GKE includes some system workloads running in the user-managed nodes which are
essential for the correct operation of the cluster. We verify that restart count
of containers in the kube-system and istio-proxy namespace stayed stable in the
last 24 hours.
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

from gcp_doctor import lint, models
from gcp_doctor.queries import gke, monitoring

# TODO(dwes): this should be configurable, maybe with a --within command-line
#             argument.
WITHIN_DAYS = 3


def run_rule(context: models.Context, report: lint.LintReportRuleInterface):
  clusters = gke.get_clusters(context)
  if not clusters:
    report.add_skipped(None, 'no clusters found')

  # Fetch the metrics for all clusters.
  query_results = monitoring.query(
      context, f"""
fetch k8s_container
| metric 'kubernetes.io/container/restart_count'
| filter (resource.namespace_name == 'kube-system' ||
          resource.namespace_name == 'istio-system') &&
         metadata.system.top_level_controller_type != 'Node'
| within {WITHIN_DAYS}d
# "bad minute" definition: number of restarts >= 1
# note: we use 5 minutes to mitigate this issue:
# https://yaqs.corp.google.com/eng/q/4852936461747486720
| align delta(5m)
| filter val() >= 1
| group_by 1d, .count
# SLO: every system container has at at leat 99.5% good minutes every day
#      (max. 7 bad minutes -- 2 bad 5 minutes, see above)
| filter val() > 2
| group_by [resource.project_id,
    cluster_name: resource.cluster_name,
    location: resource.location,
    controller: metadata.system.top_level_controller_name], [ .count ]
  """)

  # Organize the metrics per-cluster.
  per_cluster_results: Dict[tuple, Dict[str, int]] = dict()
  for ts in query_results.values():
    cluster_key = (ts['labels']['resource.project_id'],
                   ts['labels']['location'], ts['labels']['cluster_name'])
    cluster_values = per_cluster_results.setdefault(cluster_key, dict())
    cluster_values[ts['labels']['controller']] = ts

  # Go over the list of reported clusters
  for _, c in sorted(clusters.items()):
    ts_cluster_key = (c.project_id, c.location, c.name)
    if ts_cluster_key not in per_cluster_results:
      report.add_ok(c)
    else:
      report.add_failed(
          c, 'restarting: ' +
          ', '.join(per_cluster_results[ts_cluster_key].keys()))
