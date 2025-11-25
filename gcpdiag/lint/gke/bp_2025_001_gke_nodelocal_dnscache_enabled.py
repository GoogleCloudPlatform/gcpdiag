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
"""GKE clusters should have NodeLocal DNSCache enabled.

NodeLocal DNSCache improves DNS reliability and performance within the cluster
by running a local DNS cache on each node. This reduces latency and load on
kube-dns. It is a recommended best practice for most Standard clusters.
Autopilot clusters have this enabled by default.
"""

from gcpdiag import lint, models
from gcpdiag.queries import gke as gke_queries


def run_rule(context: models.Context, report: lint.LintReportRuleInterface):
  """Run the lint rule."""

  clusters = gke_queries.get_clusters(context)
  if not clusters:
    report.add_skipped(None, "no clusters found")
    return

  for _, cluster in sorted(clusters.items()):

    if cluster.status != "RUNNING":
      report.add_skipped(
          cluster, f"Cluster is not in RUNNING state (state: {cluster.status})")
      continue

    if cluster.is_autopilot:
      report.add_skipped(cluster, "NodeLocal DNSCache is default in Autopilot")
      continue

    if cluster.is_nodelocal_dnscache_enabled:
      report.add_ok(cluster)
    else:
      reason = (
          "NodeLocal DNSCache is not enabled.\n"
          "Enable it to improve DNS performance and reliability.\n"
          "You can enable it with the command:\n"
          f"  gcloud container clusters update {cluster.name} --location={cluster.location}"
          " --update-addons=NodeLocalDNS=ENABLED\n"
          "See also: https://cloud.google.com/kubernetes-engine/docs/how-to/nodelocal-dns-cache"
      )
      report.add_failed(cluster, reason=reason)
