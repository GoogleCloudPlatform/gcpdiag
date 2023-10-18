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
"""Version skew between cluster and node pool.

Difference between cluster version and node pools version should be no more
than 2 (K8s <v1.28) or 3 (K8s v1.28+) minor versions.
"""

from gcpdiag import lint, models
from gcpdiag.queries import gke

K8S_MAJOR_WITH_3_VERSIONS_SKEW = 1
K8S_MINOR_WITH_3_VERSIONS_SKEW = 28
LEGACY_SKEW = 2
CURRENT_SKEW = 3

fail_reason_template = (
    "Difference between versions of the node pool ({np_ver}) and cluster ({c_ver}) is"
    " more than {skew} minor versions")


def run_rule(context: models.Context, report: lint.LintReportRuleInterface):
  clusters = gke.get_clusters(context).values()

  if not clusters:
    report.add_skipped(None, "No GKE clusters found")

  for cluster in clusters:
    for nodepool in cluster.nodepools:

      c_ver = cluster.master_version
      np_ver = nodepool.version

      skew = LEGACY_SKEW
      if c_ver.minor >= K8S_MINOR_WITH_3_VERSIONS_SKEW or \
          c_ver.major > K8S_MAJOR_WITH_3_VERSIONS_SKEW:
        skew = CURRENT_SKEW
      major_ok = c_ver.same_major(np_ver)
      minor_ok = c_ver.diff_minor(np_ver) <= skew

      if major_ok and minor_ok:
        report.add_ok(nodepool)
      else:
        report.add_failed(nodepool,
                          reason=fail_reason_template.format(c_ver=c_ver,
                                                             np_ver=np_ver,
                                                             skew=skew))
