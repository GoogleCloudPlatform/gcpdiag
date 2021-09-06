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
"""Service Account used by the cluster exists and not disabled

Disabling or deleting service account used by the nodepool will render
this nodepool not functional. To fix - restore the default compute account
or service account that was specified when nodepool was created.
"""

from gcp_doctor import lint, models
from gcp_doctor.queries import gke, iam


def run_rule(context: models.Context, report: lint.LintReportRuleInterface):
  # Find all clusters.
  clusters = gke.get_clusters(context)
  if not clusters:
    report.add_skipped(None, 'no clusters found')
  for _, c in sorted(clusters.items()):
    # Verify service-account exists for every nodepool.
    for np in c.nodepools:
      sa = np.service_account

      # TODO: this may not work for cross-project service accounts
      accounts = iam.get_service_accounts(context)
      if sa in iam.get_service_accounts(context):
        service_account = accounts[sa]
        if service_account.disabled:
          report.add_failed(np, f'service account: {sa}\n is disabled')
      else:
        if np.has_default_service_account():
          report.add_failed(np,
                            f'default service account: {sa}\n does not exists')
        else:
          report.add_failed(np, f'service account: {sa}\n does not exists')
      report.add_ok(np)
