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
"""GKE clusters are using unique subnets.

Verify that the Google Kubernetes Engine clusters are not sharing subnets. It
is recommended to use unique subnet for each cluster.

Keep in mind that subnets may be also reused in other projects.
"""

from typing import Dict

from gcpdiag import lint, models
from gcpdiag.queries import gke


def run_rule(context: models.Context, report: lint.LintReportRuleInterface):
  clusters = gke.get_clusters(context)
  if not clusters:
    report.add_skipped(None, 'no clusters found')
  subnets: Dict[str, str] = {}
  for c in sorted(clusters.values(), key=lambda cluster: cluster.short_path):
    subnetwork_config = c.subnetwork
    if subnetwork_config is None:
      report.add_skipped(
          c, (f'Cluster "{c.name}" is using Legacy VPC with no'
              f' support for subnets. Suggest change to modern VPC.'))
      continue
    if subnetwork_config.short_path not in subnets.keys():
      subnets[subnetwork_config.short_path] = c.short_path
      report.add_ok(c)
    else:
      report.add_failed(c, (f'Subnet "{c.subnetwork.short_path}" is used by'
                            f' "{subnets[c.subnetwork.short_path]}" cluster'))
