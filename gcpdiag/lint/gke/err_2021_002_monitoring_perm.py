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
"""GKE nodes service account permissions for monitoring.

The service account used by GKE nodes should have the monitoring.metricWriter
role, otherwise ingestion of metrics won't work.
"""

from gcpdiag import lint, models
from gcpdiag.queries import gke, iam

ROLE = 'roles/monitoring.metricWriter'


def run_rule(context: models.Context, report: lint.LintReportRuleInterface):
  # Find all clusters with monitoring enabled.
  clusters = gke.get_clusters(context)
  iam_policy = iam.get_project_policy(context)
  if not clusters:
    report.add_skipped(None, 'no clusters found')
  for _, c in sorted(clusters.items()):
    if not c.has_monitoring_enabled():
      report.add_skipped(c, 'monitoring disabled')
    else:
      # Verify service-account permissions for every nodepool.
      for np in c.nodepools:
        sa = np.service_account
        if not iam.is_service_account_enabled(sa, context):
          report.add_failed(np, f'service account disabled or deleted: {sa}')
        elif not iam_policy.has_role_permissions(f'serviceAccount:{sa}', ROLE):
          report.add_failed(np, f'service account: {sa}\nmissing role: {ROLE}')
        else:
          report.add_ok(np)
