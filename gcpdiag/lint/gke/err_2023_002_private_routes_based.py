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
"""GKE private clusters are VPC-native.

Private cluster is a type of VPC-native cluster and must not be Routes-based.
VPC-native clusters use alias IP address ranges on GKE nodes and are required
for private GKE clusters and for creating clusters on Shared VPCs, as well as many
other features.
"""

from gcpdiag import lint, models
from gcpdiag.queries import gke


def run_rule(context: models.Context, report: lint.LintReportRuleInterface):
  clusters = gke.get_clusters(context)
  if not clusters:
    report.add_skipped(None, 'no clusters found')
  for _, c in sorted(clusters.items()):
    if c.is_private and not c.is_vpc_native:
      report.add_failed(c, ' is private and not VPC-native')
    else:
      report.add_ok(c)
