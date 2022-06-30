#
# Copyright 2022 Google LLC
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
"""Instance groups named ports are using unique names.

Named ports are key-value pairs that represent a port's name and number.
It is recommended to use unique port name for the same application, so that
backend service can only forward traffic to one named port at a time.
"""

from gcpdiag import lint, models
from gcpdiag.queries import gce


def prepare_rule(context: models.Context):
  groups = gce.get_instance_groups(context)
  if not groups:
    return


def run_rule(context: models.Context, report: lint.LintReportRuleInterface):
  groups = gce.get_instance_groups(context).values()
  if len(groups) == 0:
    report.add_skipped(None, 'No instance groups found')
  for g in sorted(groups):
    if g.has_named_ports():
      names = [n['name'] for n in g.named_ports]
      if len(names) > len(set(names)):
        report.add_failed(
            g, 'Instance group contains multiple ports with the same name')
      else:
        report.add_ok(g)
    else:
      report.add_ok(g)
