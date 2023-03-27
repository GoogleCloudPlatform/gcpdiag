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
"""Network bridge managed instance group is correctly configured.

If a managed instance group (MIG) is being used to route traffic to Apigee X instance
runs in a Google managed tenant project. The MIG should be created in the network which
is peered with the Apigee X instance. The MIG should also point to the correct Apigee X
instance IP.
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
    report.add_skipped(None, 'no Apigee organizations found')
    return

  if apigee_org.runtime_type == 'HYBRID':
    report.add_skipped(None, 'This rule only applies to Apigee X product')
    return

  all_instance_ips = {i.host for i in apigee.get_instances(apigee_org).values()}

  apigee_org_network_path = apigee_org.network.short_path
  apigee_org_ok_flag = True
  for mig in network_bridge_migs[context.project_id]:
    if mig.template.network.short_path != apigee_org_network_path:
      report.add_failed(
          mig,
          f'Managed instance group {mig.name} is not being created under the correct network\n'
          f'{mig.name}\'s network: {mig.template.network.short_path}\n'
          f'The network peered with Apigee: {apigee_org_network_path}')
      apigee_org_ok_flag = False
    if not mig.template.get_metadata('ENDPOINT') in all_instance_ips:
      report.add_failed(
          mig,
          f'Managed instance group {mig.name} is not pointing to any Apigee X instance.'
      )
      apigee_org_ok_flag = False

  if apigee_org_ok_flag:
    report.add_ok(apigee_org)
