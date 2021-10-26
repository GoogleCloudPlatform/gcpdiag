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

# Lint as: python3
"""Node pool service account exists and not disabled

Disabling or deleting the service account used by a node pool will render the
node pool not functional. To fix - restore the default compute account or
service account that was specified when the node pool was created.
"""

from gcpdiag import lint, models
from gcpdiag.queries import gke, iam


def run_rule(context: models.Context, report: lint.LintReportRuleInterface):
  # Find all clusters.
  clusters = gke.get_clusters(context)
  if not clusters:
    report.add_skipped(None, 'no clusters found')

  for _, c in sorted(clusters.items()):
    # Verify service-account exists for every nodepool.
    for np in c.nodepools:
      sa = np.service_account
      default_prefix = ''
      if np.has_default_service_account():
        default_prefix = 'default '
      if not iam.is_service_account_existing(sa, context.project_id):
        report.add_failed(np,
                          f'{default_prefix}service account is deleted: {sa}')
      elif not iam.is_service_account_enabled(sa, context.project_id):
        report.add_failed(np,
                          f'{default_prefix}service account is disabled: {sa}')
      else:
        report.add_ok(np)
