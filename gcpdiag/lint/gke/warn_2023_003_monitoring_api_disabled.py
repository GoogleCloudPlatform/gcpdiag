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
"""Cloud Monitoring API enabled when GKE monitoring is enabled

If Cloud Monitoring API is disabled, while GKE monitoring is enabled the
monitoring metrics won't be ingested, and thus, won't be visible in Cloud
Monitoring.
"""

from gcpdiag import lint, models
from gcpdiag.queries import apis, gke


def run_rule(context: models.Context, report: lint.LintReportRuleInterface):
  clusters = gke.get_clusters(context)
  if not clusters:
    report.add_skipped(None, 'no clusters found')
    return

  for _, c in sorted(clusters.items()):
    if not c.has_monitoring_enabled():
      report.add_skipped(c, 'GKE monitoring is disabled')
    elif c.has_monitoring_enabled() and \
        not apis.is_enabled(context.project_id, 'monitoring'):
      report.add_failed(c)
    else:
      report.add_ok(c)
