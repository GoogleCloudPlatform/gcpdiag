# Copyright 2023 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""External Load Balancer (XLB) is able to connect to the Managed Instance Group(MIG).

In order for the Apigee Managed Instance Group (MIG) to work correctly,
the External Load Balancer (XLB) network connection to the MIG must be allowed
"""

import ipaddress

from gcpdiag import lint, models
from gcpdiag.queries import apigee

network_bridge_migs = {}


# Fetch the MIGs that are communicating with the ApigeeX instances
def prefetch_rule(context: models.Context):
  network_bridge_migs[context.project_id] = (
      apigee.get_network_bridge_instance_groups(context.project_id))
  if not network_bridge_migs[context.project_id]:
    return


def run_rule(context: models.Context, report: lint.LintReportRuleInterface):

  apigee_org = apigee.get_org(context)
  if apigee_org is None:
    report.add_skipped(None, 'no Apigee organization found')
    return

  if apigee_org.runtime_type == 'HYBRID':
    report.add_skipped(None, 'This rule only applies to Apigee X product')
    return

  for mig in network_bridge_migs[context.project_id]:

    networks = apigee_org.network
    # Identify tags used by the MIG instances
    tags = mig.template.tags

    # Check connectivity from GLB to MIG instance
    ip_ranges = ['130.211.0.0/22', '35.191.0.0/16']

    for ip in ip_ranges:
      result = networks.firewall.check_connectivity_ingress(
          src_ip=ipaddress.ip_network(ip),
          ip_protocol='tcp',
          port=443,
          target_tags=tags,
      )

      if result.action == 'deny':
        report.add_failed(
            mig, f'Network connection from {ip} blocked to MIG'
            f'{mig.short_path} on port 443')
        break

    else:
      report.add_ok(mig)
