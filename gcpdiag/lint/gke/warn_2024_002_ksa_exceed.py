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
"""Number of Kubernetes service accounts not above 3000.

Fail the rule if WI is enabled and number of KSAs > `3000`
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
  _query_results_per_project_id[context.project_id] = monitoring.query(
      context.project_id, """
fetch prometheus_target
| metric 'prometheus.googleapis.com/apiserver_storage_objects/gauge'
| filter (metric.resource == 'serviceaccounts')
| group_by 1m,
    [value_apiserver_storage_objects_mean:
       mean(value.apiserver_storage_objects)]
| every 1m
| group_by [resource.cluster],
    [value_apiserver_storage_objects_mean_aggregate:
       aggregate(value_apiserver_storage_objects_mean)]
  """)


def run_rule(context: models.Context, report: lint.LintReportRuleInterface):
  clusters = gke.get_clusters(context)
  if not clusters:
    report.add_skipped(None, 'no clusters found')
    return

  per_cluster_results = {}

  # Organize the metrics per-cluster to get cluster name and KSA count.
  for ts in _query_results_per_project_id[context.project_id].values():
    try:
      cluster_name = ts['labels']['resource.cluster']
      sa_count = int(ts['values'][0][0])
      per_cluster_results[cluster_name] = sa_count
    except KeyError:
      # Ignore time series that don't have the required labels.
      pass

  for _, c in sorted(clusters.items()):
    if c.is_autopilot or c.has_workload_identity_enabled(
    ) and c.has_monitoring_enabled:
      if 'APISERVER' not in c.enabled_monitoring_components():
        report.add_skipped(c, 'API Server metrics are disabled')
        continue
      if c.name not in per_cluster_results:
        report.add_skipped(
            c, 'Unable to find serviceaccount count from APISERVER metrics')
      elif per_cluster_results[c.name] < 3000:
        report.add_ok(c)
      else:
        report.add_failed(
            c, 'Cluster has more than 3,000 Kubernetes service accounts.')
