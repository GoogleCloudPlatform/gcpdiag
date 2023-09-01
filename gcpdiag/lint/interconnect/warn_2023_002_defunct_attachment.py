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
"""VLAN attachment is in a non-functional state.

This could be because the associated Interconnect was removed,
or because the other side of a Partner attachment was deleted.
"""

from gcpdiag import lint, models
from gcpdiag.queries import interconnect


def run_rule(context: models.Context, report: lint.LintReportRuleInterface):
  attachments = interconnect.get_vlan_attachments(context.project_id)
  if not attachments:
    report.add_skipped(None, 'no vlan attachments found')
    return
  for c in attachments:
    if c.defunct_state:
      report.add_failed(c, None,
                        ' this VLAN attachment is in a non-functional state')
    else:
      report.add_ok(c)
