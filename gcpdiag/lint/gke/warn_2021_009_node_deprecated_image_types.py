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
"""GKE nodes use a containerd image.

Node images with the Docker runtime are deprecated.
Switch to the containerd image types.
https://cloud.google.com/kubernetes-engine/docs/concepts/node-images
https://cloud.google.com/kubernetes-engine/docs/concepts/using-containerd
"""

from gcpdiag import lint, models
from gcpdiag.queries import gke


def run_rule(context: models.Context, report: lint.LintReportRuleInterface):
  clusters = gke.get_clusters(context)
  if not clusters:
    report.add_skipped(None, 'no clusters found')
  for _, cluster in sorted(clusters.items()):
    if not cluster.nodepools:
      report.add_skipped(None, 'no nodepools found')
      continue
    for nodepool in cluster.nodepools:
      if nodepool.config.image_type.find('CONTAINERD') != -1:
        report.add_ok(nodepool)
      elif nodepool.config.image_type.find('WINDOWS') != -1:
        if nodepool.version < gke.Version('1.21.1'):
          report.add_skipped(
              nodepool, f'GKE windows node pool {nodepool.version}. '
              f'the Docker container runtime is deprecated '
              f'only with windows image versions >= 1.21.1')
        else:
          report.add_failed(
              nodepool,
              f'nodepool is using the deprecated Docker container runtime '
              f'(nodepool version: {nodepool.version}, image type: {nodepool.config.image_type})'
          )
      else:
        if nodepool.version < gke.Version('1.19.0'):
          report.add_skipped(
              nodepool, f'GKE node pool {nodepool.version}. '
              f'the Docker container runtime is deprecated '
              f'only with image versions >= 1.19')
        else:
          report.add_failed(
              nodepool,
              f'nodepool is using the deprecated Docker container runtime '
              f'(nodepool version: {nodepool.version}, image type: {nodepool.config.image_type})'
          )
