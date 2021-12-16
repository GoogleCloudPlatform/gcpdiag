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
"""GKE masters of private clusters can reach the nodes.

Masters must be allowed to reach the nodes via tcp:443 and tcp10250.
"""

from gcpdiag import lint, models
from gcpdiag.queries import gke


def _run_rule_cluster(report: lint.LintReportRuleInterface, c: gke.Cluster):
  network = c.network
  if not c.nodepools:
    report.add_skipped(c, 'no nodepools')
    return
  np = next(iter(c.nodepools))
  if not c.is_private:
    report.add_skipped(c, 'public cluster')
    return

  # Verify connectivity
  for masters_net in c.masters_cidr_list:
    for p in [443, 10250]:
      result = network.firewall.check_connectivity_ingress(
          src_ip=masters_net,
          ip_protocol='tcp',
          port=p,
          target_service_account=np.service_account,
          target_tags=np.node_tags)
      if result.action == 'deny':
        report.add_failed(
            c, 'connections from %s to port %s blocked by %s' %
            (masters_net, p, result.matched_by_str))
        return
  report.add_ok(c)


def run_rule(context: models.Context, report: lint.LintReportRuleInterface):
  clusters = gke.get_clusters(context)
  for _, c in sorted(clusters.items()):
    _run_rule_cluster(report, c)
