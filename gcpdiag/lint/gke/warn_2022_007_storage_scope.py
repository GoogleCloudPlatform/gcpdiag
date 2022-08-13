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
"""GKE nodes have Storage API access scope to retrieve build artifacts

GKE nodes must have access to storage.googleapis.com to pull binaries/configs for
node bootstrapping process and/or pull build artifacts from private Container
or Artifact Registry repositories. Nodes may report connection timeouts during node bootstrapping
or `401 Unauthorized` if they cannot pull from a private repositories.
"""

from gcpdiag import lint, models
from gcpdiag.queries import gke

required_storage_scope = [
    'https://www.googleapis.com/auth/devstorage.read_only',
    'https://www.googleapis.com/auth/devstorage.read_write',
    'https://www.googleapis.com/auth/devstorage.full_control',
    'https://www.googleapis.com/auth/cloud-platform',
    'https://www.googleapis.com/auth/cloud-platform.read-only'
]


def run_rule(context: models.Context, report: lint.LintReportRuleInterface):
  clusters = gke.get_clusters(context)
  if not clusters:
    report.add_skipped(None, 'no clusters found')

  for cluster in sorted(clusters.values()):
    for nodepool in cluster.nodepools:

      if not cluster.nodepools:
        report.add_skipped(None, 'no nodepools found')

      if any(s in nodepool.config.oauth_scopes for s in required_storage_scope):
        report.add_ok(nodepool)
      else:
        report.add_failed(nodepool, None)
