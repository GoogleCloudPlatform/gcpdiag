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
"""VLAN attachments deployed in same metro are in different EADs (Edge Availability Domains).

To establish 99.99% high availability for interconnects, please ensure the following conditions:
      - Two metros are required, each metro has two attachments;
      - Attachments in same metro are in different EADs;
      - Two regions are required with four cloud router TASKS evenly distributed;
      - Global routing must be enabled on those cloud routers.
"""

from typing import Dict

from gcpdiag import lint, models
from gcpdiag.queries import crm, interconnect


def run_rule(context: models.Context, report: lint.LintReportRuleInterface):
  project = crm.get_project(context.project_id)
  attachments = interconnect.get_vlan_attachments(context.project_id)
  lookup: Dict[tuple[str, str], Dict] = {}
  ha_pairs: Dict[tuple[str, str], Dict] = {}

  if len(attachments) == 0:
    report.add_skipped(None, 'no vlan attachments found')
    return

  for attachment in attachments:
    region_metro = (attachment.region, attachment.metro)
    eads = lookup.setdefault(region_metro, {})
    eads.setdefault(attachment.ead, []).append(attachment.name)

  # filter the region_metro that don't have EADs > 1 with attachments
  ha_pairs = {k: v for k, v in lookup.items() if len(v) > 1}

  if len(ha_pairs) < 2:
    report.add_failed(
        project,
        'There are no vlan attachment pairs that can establish 99.99% high availability.'
    )
  else:
    result = (
        'The following vlan attachments could be used to establish 99.99% high avaiablibility:\n'
    )
    for region_metro, attachment_list in ha_pairs.items():
      region, metro = region_metro
      result = result + (
          f'\n * region:{region} and metro:{metro} '
          f'have the following attachments in different EADs: {attachment_list}'
      )
    note = '''
      \nYou can use vlan attachments from above list to establsh 99.99% high availability for interconnects, please ensure the following conditions:
          - Two metros are required, each metro has two attachments;
          - Attachments in same metro are in different EADs;
          - Two regions are required with four cloud router TASKS evenly distributed;
          - Global routing must be enabled on those cloud routers.'''
    report.add_ok(project, result + note)
