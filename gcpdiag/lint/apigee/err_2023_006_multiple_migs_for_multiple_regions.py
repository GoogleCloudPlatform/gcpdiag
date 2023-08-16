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
"""A multi-region setup requires a separate MIG for each region.

Each Apigee X region should have a MIG created in the same region.
Otherwise the traffic will only be routed to one region.
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

  instances_list = apigee.get_instances(apigee_org)
  mig_regions = []

  for mig in network_bridge_migs[context.project_id]:
    mig_regions.append(mig.region)

  for instance in sorted(instances_list.values(),
                         key=lambda instance: instance.name):
    curr_instance_location = instance.location

    if not curr_instance_location in mig_regions:
      report.add_failed(
          instance,
          (f'Instance {instance.name} in region {curr_instance_location} '
           f'has no MIG in the region {curr_instance_location}'))
    else:
      report.add_ok(instance)
