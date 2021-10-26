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
than 2 minor versions.
"""

from gcpdiag import lint, models
from gcpdiag.queries import gke

fail_reason_template = (
    "Difference between versions of the node pool ({np_ver}) and cluster ({c_ver}) is"
    " more than two minor versions")


def run_rule(context: models.Context, report: lint.LintReportRuleInterface):
  clusters = gke.get_clusters(context).values()

  if not clusters:
    report.add_skipped(None, "No GKE clusters found")

  for cluster in clusters:
    for nodepool in cluster.nodepools:

      c_ver = cluster.master_version
      np_ver = nodepool.version

      major_ok = c_ver.same_major(np_ver)
      minor_ok = c_ver.diff_minor(np_ver) <= 2

      if major_ok and minor_ok:
        report.add_ok(nodepool)
      else:
        report.add_failed(nodepool,
                          reason=fail_reason_template.format(c_ver=c_ver,
                                                             np_ver=np_ver))
