# Copyright 2025 Google LLC
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
"""
This runbook module checks for issues related to Cloud NAT, which is a common
source of networking failures for Dataproc clusters with internal IP addresses.
"""

from gcpdiag import dataproc
from gcpdiag.queries import apis, crm, dataproc, gce, iam, network

class CloudNatRule(dataproc.BaseRule):
  """Checks for missing Cloud NAT on the cluster's subnet."""

  def run(self, context: runbook.RunbookContext):
    """Checks if the cluster's subnet is served by a Cloud NAT gateway."""
    cluster = dataproc.get_cluster(context.project_id, context.region, context.cluster_name)
    subnet = network.get_subnet(cluster.subnet_uri)
    router = network.get_router_for_subnet(subnet)

    if not router or not router.has_nat:
      runbook.add_failed_rule(
          report=runbook.Report(
              short_desc='Cloud NAT is not configured for the cluster\'s subnet.',
              long_desc=(
                  'Dataproc clusters with internal IP addresses require a Cloud NAT gateway to reach '
                  'non-Google internet resources (e.g., package repositories, external APIs). '
                  f'The subnet "{subnet.name}" is not currently served by a Cloud NAT gateway.'
              ),
              remediation=(
                  'To fix this, create a Cloud Router in the same region and VPC as your cluster, '
                  'and then configure a Cloud NAT gateway on that router to serve your subnet.'
              )
          )
      )
    else:
      runbook.add_ok_rule(
          report=runbook.Report(
              short_desc='Cloud NAT is correctly configured for the cluster\'s subnet.'
          )
      )

  @property
  def solution(self):
    return (
        '**Cloud NAT** allows virtual machine (VM) instances without external IP addresses and private Google Kubernetes Engine (GKE) clusters '
        'to connect to the internet.'
    )
