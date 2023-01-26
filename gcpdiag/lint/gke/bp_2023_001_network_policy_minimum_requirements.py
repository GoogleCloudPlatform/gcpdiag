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
"""GKE network policy minimum requirements

The recommended minimum cluster size to run network policy enforcement is three e2-medium
instances to ensure redundency, high availibilty and to avoid down time due to maintanence
activities.

Network policy is not supported for clusters whose nodes are f1-micro or g1-small instances,
as the resource requirements are too high. Enabling this feature on such machines might lead
to user worklaods not getting scheduled or having very little resources available as
kube-system workloads will be consuming all or most resources.
"""

from gcpdiag import lint, models
from gcpdiag.queries import gke


def run_rule(context: models.Context, report: lint.LintReportRuleInterface):
  clusters = gke.get_clusters(context)
  if not clusters:
    report.add_skipped(None, 'no clusters found')

  for _, c in sorted(clusters.items()):
    # Skipping check for autopilot clusters as begining from version 1.22.7-gke.1500
    # and later and versions 1.23.4-gke.1500 and later have Dataplane V2 enabled by default

    # Check if cluster has dataplane V2 which has network ploicy enabled
    if c.has_dpv2_enabled():
      report.add_skipped(c, 'Dataplane V2 is enabled in the cluster')
      continue

    if not c.has_network_policy_enabled():
      report.add_skipped(
          c, 'network policy enforcement is disabled in the cluster')
      continue

    # check for number of nodes in the cluster
    if c.current_node_count < 3:
      report.add_failed(c, 'Node count: ' + str(c.current_node_count))
      continue

    # check nodepool node's machine type
    node_failure = False
    for n in c.nodepools:
      machine_type = n.get_machine_type()
      if machine_type in ('f1-micro', 'g1-small'):
        report.add_failed(n, 'node\'s machine type is: ' + machine_type)
        node_failure = True

    if not node_failure:
      report.add_ok(c)
