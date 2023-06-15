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
"""Private Google Access (PGA) for subnet of Managed Instance Group is enabled.

If a managed instance group (MIG) is being used to route traffic to Apigee X instance
running in a Google managed tenant project, the MIG's subnet should have Private
Google Access (PGA) enabled.
"""

from gcpdiag import lint, models
from gcpdiag.queries import apigee

network_bridge_migs = {}


def prefetch_rule(context: models.Context):
  network_bridge_migs[
      context.project_id] = apigee.get_network_bridge_instance_groups(
          context.project_id)


def run_rule(context: models.Context, report: lint.LintReportRuleInterface):

  if not network_bridge_migs[context.project_id]:
    report.add_skipped(None, 'no Apigee network bridge MIGs found')
    return

  apigee_org = apigee.get_org(context)
  if apigee_org is None:
    report.add_skipped(None, 'no Apigee organization found')
    return

  if apigee_org.runtime_type == 'HYBRID':
    report.add_skipped(None, 'This rule only applies to Apigee X product')
    return

  for mig in network_bridge_migs[context.project_id]:
    network = mig.template.network

    # find subnets connected to Apigee via Managed Instance Group
    for subnet in network.subnetworks.values():
      if subnet.region == mig.region:
        is_private_ip_google_access = subnet.is_private_ip_google_access()

        if not is_private_ip_google_access:
          report.add_failed(
              mig, (f'Private Google Access is not enabled on '
                    f'subnetwork {subnet.short_path} with region {mig.region} '
                    f'in network {network.short_path}'))
        else:
          report.add_ok(mig)
