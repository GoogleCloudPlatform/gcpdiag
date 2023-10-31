# Copyright 2023 Google LLC
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
"""GKE Workload Identity is enabled

Workload Identity is the recommended way for your workloads running on
Google Kubernetes Engine (GKE) to access Google Cloud services in a secure
and manageable way. It lets you assign distinct, fine-grained identities
and authorization for each application in your cluster.
The sensitive node's metadata is also protected by Workload Identity.
"""

from gcpdiag import lint, models
from gcpdiag.queries import gke

clusters_by_project = {}


def prepare_rule(context: models.Context):
  clusters_by_project[context.project_id] = gke.get_clusters(context)


def run_rule(context: models.Context, report: lint.LintReportRuleInterface):
  clusters = clusters_by_project[context.project_id]
  if not clusters:
    report.add_skipped(None, 'no clusters found')
  for _, c in sorted(clusters.items()):
    if c.is_autopilot or c.has_workload_identity_enabled():
      report.add_ok(c)
    else:
      report.add_failed(c)
