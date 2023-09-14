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
"""The interconnect link is undergoing a maintenance window.

Pleaes check the email sent to the technical contacts for further details about the maintenance.

"""

from gcpdiag import lint, models
from gcpdiag.queries import interconnect


def run_rule(context: models.Context, report: lint.LintReportRuleInterface):
  interconnects = interconnect.get_links(context.project_id)
  if not interconnects:
    report.add_skipped(None, 'no Inteconnect links found')
    return
  for c in interconnects:
    if c.under_maintenance:
      report.add_failed(
          c, None, ' this Interconnect link is currently under maintenance')
    else:
      report.add_ok(c)
