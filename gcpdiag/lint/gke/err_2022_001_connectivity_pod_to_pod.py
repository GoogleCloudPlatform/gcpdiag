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
"""GKE connectivity: pod to pod communication.

Traffic between all pods on a cluster is required by the Kubernetes networking
model. Following protocols must be allowed: TCP, UDP, SCTP, ICMP, ESP, AH.
"""

from gcpdiag import lint, models, utils
from gcpdiag.queries import gke

# All ports must be allowed, but only verify a fixed set.
VERIFY_PORTS = {  #
    'tcp': [53, 80, 443, 8080, 10000],
    'udp': [53, 1000, 10000]
}


def prefetch_rule(context: models.Context):
  # Prefetch networks and subnetworks
  clusters = gke.get_clusters(context)
  for c in clusters.values():
    subnets = c.network.subnetworks
    del subnets


def _run_rule_cluster(report: lint.LintReportRuleInterface, c: gke.Cluster):
  network = c.network
  if not c.nodepools:
    report.add_skipped(c, 'no nodepools')
    return

  src_net = c.pod_ipv4_cidr

  for np in c.nodepools:
    for (proto, port) in utils.iter_dictlist(VERIFY_PORTS):
      result = network.firewall.check_connectivity_ingress(
          src_ip=src_net,
          ip_protocol=proto,
          port=port,
          target_service_account=np.service_account,
          target_tags=np.node_tags)

      if result.action == 'deny':
        report.add_failed(
            c, (f'connections from {src_net} to {proto}:{port} blocked by '
                f'{result.matched_by_str} (node pool: {np.name})'))
        return
  report.add_ok(c)


def run_rule(context: models.Context, report: lint.LintReportRuleInterface):
  clusters = gke.get_clusters(context)
  if not clusters:
    report.add_skipped(None, 'no clusters found')
  for _, c in sorted(clusters.items()):
    _run_rule_cluster(report, c)
