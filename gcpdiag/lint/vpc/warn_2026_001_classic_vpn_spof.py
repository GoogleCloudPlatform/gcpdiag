# Copyright 2026 Google LLC
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

"""VPC networks only use HA VPN for hybrid connectivity.

Classic VPN (target-vpn-gateways) does not offer a high availability SLA
and lacks automatic failover. This poses a risk of complete connectivity loss
between GCP and the peer network during maintenance or other issues.
It is recommended to migrate to HA VPN for critical workloads.
"""

from gcpdiag import lint, models, utils
from gcpdiag.queries import crm, gce


def run_rule(context: models.Context, report: lint.LintReportRuleInterface):
  try:
    target_vpn_gateways = gce.get_target_vpn_gateways(context)
  except utils.GcpApiError as e:
    report.add_skipped(None, f'Failed to query target VPN gateways: {e}')
    return

  if not target_vpn_gateways:
    report.add_ok(
      crm.get_project(context.project_id),
      'No Classic VPN gateways (target-vpn-gateways) found.',
    )
  else:
    for self_link in sorted(target_vpn_gateways):
      gateway = target_vpn_gateways[self_link]
      report.add_failed(
        resource=gateway,
        reason=(
          f"Classic VPN Gateway '{gateway.name}' in region '{gateway.region}' "
          f'({gateway.self_link}) found. Classic VPN is susceptible to being a single '
          'point of failure and lacks an HA SLA. Consider migrating to HA VPN.'
        ),
      )
