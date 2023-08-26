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
"""On-premises hosts can communicate with the service producer's network

When you create a private connection,  the VPC network and service producer's
network only exchange subnet routes by default.

Enabling the export of custom routes to this private connection allows
on-premises hosts to access the service producer's network via private
services access.
"""

from gcpdiag import lint, models
from gcpdiag.queries import interconnect, network


def run_rule(context: models.Context, report: lint.LintReportRuleInterface):
  networks = network.get_networks(context.project_id)

  if not networks:
    report.add_skipped(None, 'no networks found')
    return

  for net in networks:
    peerings = net.peerings
    all_custom_routes_exported = True

    for peering in peerings:
      if peering.name == 'servicenetworking-googleapis-com':
        if not peering.exports_custom_routes:
          all_custom_routes_exported = False
          break
        else:
          report.add_ok(net)

    if not all_custom_routes_exported:
      routes = network.get_routes(context.project_id)
      for route in routes:
        if ((route.next_hop_hub or route.next_hop_vpn_tunnel) and
            (net.full_path in route.network)):
          report.add_failed(
              net, 'Private Service Access not exporting custom routes.')
          break
      attachments = interconnect.get_vlan_attachments(context.project_id)
      if attachments:
        report.add_failed(
            net, 'Private Service Access not exporting custom routes.')
        break
