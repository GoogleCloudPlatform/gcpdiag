# Copyright 2023 Google LLC
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
"""DNSSEC is enabled for public zones.

It is recommended to enable DNSSEC for public zones.
"""

from gcpdiag import lint, models
from gcpdiag.queries import network


def run_rule(context: models.Context, report: lint.LintReportRuleInterface):
  zones = network.get_zones(context.project_id)
  if not zones:
    report.add_skipped(None, 'no zones found')
    return
  for c in zones:
    if (c.is_public and not c.dnssec_config_state):
      report.add_failed(c, None, ' DNSSEC is disabled for this public zone')
    else:
      report.add_ok(c)
