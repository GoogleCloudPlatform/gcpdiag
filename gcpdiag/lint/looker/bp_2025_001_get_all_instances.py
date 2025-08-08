# Copyright 2025 Google LLC
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
"""List all Looker Core instances in given GCP project.
Probable reasons for failure would be insufficient permissions or corrupted state of instances.
"""

from gcpdiag import lint, models
from gcpdiag.queries import looker


def run_rule(context: models.Context, report: lint.LintReportRuleInterface):
  instances = looker.get_instances(context)
  if not instances:
    report.add_skipped(None, 'No instances found')
  for _, c in sorted(instances.items()):
    if c.name == '':
      report.add_failed(c)
    else:
      report.add_ok(c, c.status)
