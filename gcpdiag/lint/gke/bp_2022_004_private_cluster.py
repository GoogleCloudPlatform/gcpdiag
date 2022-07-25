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
"""GKE clusters are set to Private.

Verify that the Google Kubernetes Engine clusters do not attach external IPs directly to the nodes. Instead a NAT Gateway / Global Load Balancer should be used.
"""

from typing import Dict

from gcpdiag import lint, models
from gcpdiag.queries import gke


def run_rule(context: models.Context, report: lint.LintReportRuleInterface):
  clusters = gke.get_clusters(context)
  if not clusters:
    report.add_skipped(None, 'no clusters found')
  for _, c in sorted(clusters.items()):
    if not c.is_private:
      report.add_failed(c, ' is not a private cluster')
    else:
      report.add_ok(c)
