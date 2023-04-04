# Copyright 2021 Google LLC
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
"""GKE logging and monitoring enabled.

Disabling either one of logging (SYSTEM, WORKLOADS) and
monitoring (aka "GKE Cloud Operations") impacts the
ability to effectively and efficiently troubleshoot cluster issues.
"""

from gcpdiag import lint, models
from gcpdiag.queries import gke


def run_rule(context: models.Context, report: lint.LintReportRuleInterface):
  clusters = gke.get_clusters(context)
  if not clusters:
    report.add_skipped(None, 'no clusters found')
  for _, c in sorted(clusters.items()):
    if not c.is_autopilot:
      disabled: list[str] = []
      if c.has_logging_enabled() and \
        'WORKLOADS' not in c.enabled_logging_components():
        disabled.append('workload logs')
      elif not c.has_logging_enabled():
        disabled.append('logging')

      if not c.has_monitoring_enabled():
        disabled.append('monitoring')

      if disabled:
        report.add_failed(c, ' and '.join(disabled) + ' are disabled')
      else:
        report.add_ok(c)
