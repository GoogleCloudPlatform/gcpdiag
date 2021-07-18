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
"""GKE nodes w/o workload identity don't use the GCE default service account.

The GCE default service account has more permissions than are required to run
your Kubernetes Engine cluster. You should create and use a minimally privileged
service account.

Reference: Hardening your cluster's security
  https://cloud.google.com/kubernetes-engine/docs/how-to/hardening-your-cluster#use_least_privilege_sa
"""

from gcp_doctor import lint, models
from gcp_doctor.queries import gke

ROLE = 'roles/logging.logWriter'


def run_rule(context: models.Context, report: lint.LintReportRuleInterface):
  # Find all clusters.
  clusters = gke.get_clusters(context)
  if not clusters:
    report.add_skipped(None, 'no clusters found')
  for _, c in sorted(clusters.items()):
    # Verify service-account for every standard nodepool.
    for np in c.nodepools:
      if np.has_workload_identity_enabled():
        report.add_skipped(np, 'workload identity enabled')
      elif np.has_default_service_account():
        report.add_failed(np, 'node pool uses the GCE default service account')
      else:
        report.add_ok(np)
