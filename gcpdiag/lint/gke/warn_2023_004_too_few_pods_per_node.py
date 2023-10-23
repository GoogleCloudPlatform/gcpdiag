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
"""A Node Pool doesn't have too low `maxPodsPerNode` number

Modern GKE clusters could run multiple system DaemonSets, and enabling a GKE
feature could add another DaemonSet or two. 7+ DaemonSets is the norm for an
average GKE cluster. Low `maxPodsPerNode` number could prevent normal workload
scheduling as all the available slots could be occupied by system or custom
DaemonSet pods. `maxPodsPerNode` >= 16 should be a safer option."""

from gcpdiag import lint, models
from gcpdiag.queries import gke

TOO_FEW_PODS_PER_NODE_THRESHOLD = 15


def run_rule(context: models.Context, report: lint.LintReportRuleInterface):
  clusters = gke.get_clusters(context).values()

  if not clusters:
    report.add_skipped(None, "No GKE clusters found")

  for cluster in clusters:
    for nodepool in cluster.nodepools:

      if nodepool.max_pod_per_node > TOO_FEW_PODS_PER_NODE_THRESHOLD:
        report.add_ok(nodepool)
      else:
        report.add_failed(
            nodepool,
            reason=
            f"the nodepool has too low `maxPodsPerNode` number: {nodepool.max_pod_per_node}"
        )
