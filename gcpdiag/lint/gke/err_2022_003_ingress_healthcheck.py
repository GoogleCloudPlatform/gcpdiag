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
"""GKE connectivity: load balancer to node communication (ingress).

In order for the Ingress service to work correctly, the network connection from
the load balancer must be allowed.
"""
import re

from gcpdiag import lint, models
from gcpdiag.queries import gke
from gcpdiag.queries.network import VpcFirewallRule

FIREWALL_RULE_NAME_PATTERN = re.compile(r'k8s-fw-l7-.*')


def _get_rule_allowed_ports(rule: VpcFirewallRule):
  """Return list of tuples defined in the rule

  For example:
  [
    (IPv4Network('130.211.0.0/22'), '30000')
    (IPv4Network('35.191.0.0/16'), '30000')
  ]
  """
  result = []
  for a in rule.allowed:
    for port in a.get('ports', []):
      # in the rule definition we might have one port or port range
      # in the 2nd case we will use first value of the range to test connectivity
      # finally we need to combine ports with source ranges
      for source in rule.source_ranges:
        result.append((source, port.split('-')[0]))
        if '-' in port:
          result.append((source, port.split('-')[1]))
  return result


def run_rule(context: models.Context, report: lint.LintReportRuleInterface):
  clusters = gke.get_clusters(context)
  if not clusters:
    report.add_skipped(None, 'no clusters found')
    return

  for _, c in sorted(clusters.items()):
    for np in c.nodepools:
      tags = np.node_tags
      if c.is_autopilot:
        # use default tags for autopilot clusters
        tags = [f'gke-{c.name}-{c.cluster_hash}-node']
      rules = c.network.firewall.get_vpc_ingress_rules(
          name_pattern=FIREWALL_RULE_NAME_PATTERN, target_tags=tags)
      if not rules:
        report.add_skipped(np, 'no ingress detected')
        break
      failed = False
      for r in rules:
        for src_range, port in _get_rule_allowed_ports(r):
          result = c.network.firewall.check_connectivity_ingress(
              src_ip=src_range,
              ip_protocol='tcp',
              port=int(port),
              target_service_account=np.service_account,
              target_tags=np.node_tags)
          if result.action == 'deny':
            failed = True
            report.add_failed(
                np,
                f'connections from {src_range} to port {port} blocked by {result.matched_by_str}'
            )
            break
      if not failed:
        report.add_ok(np)
