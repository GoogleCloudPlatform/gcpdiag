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
"""GKE master version available for new clusters.

The GKE master version should be a version that is available
for new clusters. If a version is not available it could mean
that it is deprecated, or possibly retired due to issues with
it.
"""

from gcpdiag import lint, models
from gcpdiag.queries import gke


def run_rule(context: models.Context, report: lint.LintReportRuleInterface):
  clusters = gke.get_clusters(context)
  if not clusters:
    report.add_skipped(None, 'no clusters found')
  for _, c in sorted(clusters.items()):
    if c.release_channel:
      report.add_skipped(c, 'release channel: ' + c.release_channel)
      continue

    valid_master_versions = gke.get_valid_master_versions(
        c.project_id, c.location)
    if c.master_version not in valid_master_versions:
      report.add_failed(c,
                        'valid versions: ' + ', '.join(valid_master_versions),
                        c.master_version)
    else:
      report.add_ok(c, c.master_version)
