#
# Copyright 2024 Google LLC
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

# Lint as: python3
"""Instance has a public ip address

If the Compute Engine instance does not have a public ip address, then
the SSH button will be disabled in the SSH in browser UI.
"""

from gcpdiag import lint, models
from gcpdiag.queries import gce


def run_rule(context: models.Context, report: lint.LintReportRuleInterface):
  instances = gce.get_instances(context).values()

  if instances:
    for instance in sorted(instances, key=lambda i: i.name):
      if not instance.is_public_machine():
        report.add_failed(instance, "Instance does not have a public address.")
      else:
        report.add_ok(instance)
  else:
    report.add_skipped(None, "No instances found")
