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
"""Customer's network is peered to Apigee's network

There should be a VPC peering connection between customer's network and the Apigee X
instance runs in a Google managed tenant project
"""
import re

from gcpdiag import lint, models
from gcpdiag.queries import apigee

APIGEE_NETWORK = 'servicenetworking'


def run_rule(context: models.Context, report: lint.LintReportRuleInterface):
  apigee_org = apigee.get_org(context)
  if apigee_org is None:
    report.add_skipped(None, 'no Apigee organizations found')
    return

  if apigee_org.runtime_type == 'HYBRID':
    report.add_skipped(None, 'This rule only applies to Apigee X product')
    return

  # Check whether there is a VPC peering connection with Apigee runtime instances or not
  is_peered_to_apigee = False

  for peer in apigee_org.network.peerings:
    match = re.match(
        r'https://www.googleapis.com/compute/([^/]+)/'
        'projects/([^/]+)/([^/]+)/networks/(?P<network>[^/]+)$', peer.url)

    if not match:
      raise ValueError(f"can't parse peering network url: {peer.url!r}")

    peered_network = match.group('network')

    if peered_network == APIGEE_NETWORK:
      if peer.state == 'ACTIVE':
        is_peered_to_apigee = True
        break

      else:
        report.add_failed(
            apigee_org, (f'peered connection to Apigee {peer.name} in network '
                         f'{apigee_org.network.short_path} is not active.'))
        return

  if is_peered_to_apigee:
    report.add_ok(apigee_org)
  else:
    report.add_failed(
        apigee_org, (f'Customer VPC network {apigee_org.network.short_path} is '
                     'not correctly peered to Apigee\'s network'))
