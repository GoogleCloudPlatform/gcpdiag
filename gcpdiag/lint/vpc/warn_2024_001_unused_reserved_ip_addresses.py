# Copyright 2024 Google LLC
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
"""No Unused reserved IP addresses are found.

We can reserve IP addresses and persists until we explicitly release it.
Unused reserved IP addresses over the time will cause extra money.
Make sure you identify and release those IP addresses.
"""

from gcpdiag import lint, models
from gcpdiag.queries import network

ip_addresses = {}


def run_rule(context: models.Context, report: lint.LintReportRuleInterface):

  ip_addresses[context.project_id] = network.get_addresses(context.project_id)

  addresses = ip_addresses[context.project_id]

  if not addresses:
    report.add_skipped(None, 'no Reserved IP addresses found')
    return

  for address in addresses:
    if address.status == 'RESERVED':
      report.add_failed(address, 'Unused Reserved IP address found')
    else:
      report.add_ok(address)
