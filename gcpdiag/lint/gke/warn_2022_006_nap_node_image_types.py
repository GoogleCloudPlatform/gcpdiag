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
"""GKE NAP nodes use a containerd image.

Node images with the docker runtime are deprecated. Please switch to the
containerd image types.
"""

from gcpdiag import lint, models
from gcpdiag.queries import gke


def run_rule(context: models.Context, report: lint.LintReportRuleInterface):
  clusters = gke.get_clusters(context)
  if not clusters:
    report.add_skipped(None, 'no clusters found')
  for _, c in sorted(clusters.items()):
    if c.nap_node_image_type is None:
      report.add_skipped(c, 'Node Auto Provisioning Disabled')
      continue
    if 'CONTAINERD' in c.nap_node_image_type:
      report.add_ok(c, 'Node Type: ' + c.nap_node_image_type)
    else:
      report.add_failed(c, 'Node Type: ' + c.nap_node_image_type)
