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
"""VLAN attachment is using Dataplan V1.

Dataplane V1 doesn't support certain feature such as BFD, consider upgrading to Datapalne V2.
For more information:
https://cloud.google.com/network-connectivity/docs/interconnect/concepts/terminology#dataplaneVersion
"""

from gcpdiag import lint, models
from gcpdiag.queries import interconnect


def run_rule(context: models.Context, report: lint.LintReportRuleInterface):
  attachments = interconnect.get_vlan_attachments(context.project_id)
  if not attachments:
    report.add_skipped(None, 'no vlan attachments found')
    return
  for c in attachments:
    if c.legacy_dataplane:
      report.add_failed(c, None, ' this VLAN attachment is using Dataplane V1')
    else:
      report.add_ok(c)
