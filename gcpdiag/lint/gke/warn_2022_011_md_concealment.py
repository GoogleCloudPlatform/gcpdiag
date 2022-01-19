# Copyright 2022 Google LLC
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
"""GKE metadata concealment is not in use

Metadata concealment is scheduled to be deprecated and removed in the future.
Workload Identity replaces the need to use metadata concealment and the two
approaches are incompatible. It is recommended that you use Workload Identity
instead of metadata concealment.
"""

from gcpdiag import lint, models
from gcpdiag.queries import gke


def run_rule(context: models.Context, report: lint.LintReportRuleInterface):
  # Find all clusters.
  clusters = gke.get_clusters(context)
  if not clusters:
    report.add_skipped(None, 'no clusters found')
  for _, c in sorted(clusters.items()):
    # Verify MD concealment for every standard nodepool.
    for np in c.nodepools:
      if np.has_md_concealment_enabled():
        report.add_failed(np, 'metadata concealment is in use')
      else:
        report.add_ok(np)
