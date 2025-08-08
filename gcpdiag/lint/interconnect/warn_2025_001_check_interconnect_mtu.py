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
"""VLAN attachment MTU matches VPC MTU

Mismatched MTU may cause potential connection issues.
Please check VLAN attachment and VPC network MTU configurations.

"""

from gcpdiag import lint, models
from gcpdiag.queries import interconnect, network


def run_rule(context: models.Context, report: lint.LintReportRuleInterface):
  attachments = interconnect.get_vlan_attachments(context.project_id)
  if not attachments:
    report.add_skipped(None, 'no vlan attachments found')
    return

  for vlan in attachments:
    vlan_router = network.get_router_by_name(project_id=context.project_id,
                                             region=vlan.region,
                                             router_name=vlan.router)

    if not vlan_router:
      report.add_skipped(vlan, 'no vlan router found')
      continue

    vlan_network_name = vlan_router.get_network_name()
    vlan_network = network.get_network(project_id=context.project_id,
                                       network_name=vlan_network_name)
    if not vlan_network:
      report.add_skipped(vlan, 'no vlan network found')

    if vlan.mtu != vlan_network.mtu:
      report.add_failed(
          vlan, None,
          f' MTU mismatch: {vlan.mtu} vs VPC MTU {vlan_network.mtu}')
    else:
      report.add_ok(vlan)
