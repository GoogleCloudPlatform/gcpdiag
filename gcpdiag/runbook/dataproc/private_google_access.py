# Copyright 2025 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS-is" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""
This runbook module checks for issues related to Private Google Access,
which is a common source of networking failures for Dataproc clusters that
do not have external IP addresses.
"""

from gcpdiag import dataproc
from gcpdiag.queries import apis, crm, dataproc, gce, iam, network

class PrivateGoogleAccessRule(runbook.BaseRule):
  """Checks for missing Private Google Access on the cluster's subnet."""

  def pre_run_check(self, context: runbook.RunbookContext):
    """Checks that the cluster exists and has a subnet."""
    cluster = dataproc.get_cluster(context.project_id, context.region,
                                   context.cluster_name)
    if not cluster:
      runbook.add_skipped_rule(
          report=runbook.Report(
              short_desc=
              f'Dataproc cluster "{context.cluster_name}" not found in project "{context.project_id}".'
          ))
    elif not cluster.subnet_uri:
      runbook.add_skipped_rule(
          report=runbook.Report(
              short_desc=
              f'Dataproc cluster "{context.cluster_name}" does not have a subnet URI.'
          ))

  def run(self, context: runbook.RunbookContext):
    """Checks the PGA setting on the cluster's subnet."""
    cluster = dataproc.get_cluster(context.project_id, context.region,
                                   context.cluster_name)
    subnet = network.get_subnet(cluster.subnet_uri)

    if not subnet.private_ip_google_access:
      runbook.add_failed_rule(
          report=runbook.Report(
              short_desc=
              'Private Google Access is not enabled on the cluster\'s subnet.',
              long_desc=(
                  'Dataproc clusters with internal IP addresses require Private Google Access (PGA) '
                  'to reach Google APIs and services. PGA is currently disabled on the subnet '
                  f'"{subnet.name}".'),
              remediation=(
                  'To fix this, enable Private Google Access on the subnet. You can do this by running: \n'
                  f'`gcloud compute networks subnets update {subnet.name} --region={subnet.region} --enable-private-ip-google-access`'
              )))
    else:
      runbook.add_ok_rule(
          report=runbook.Report(
              short_desc=
              'Private Google Access is correctly enabled on the cluster\'s subnet.'
          ))

  @property
  def solution(self):
    return (
        '**Private Google Access (PGA)** allows virtual machine (VM) instances that only have internal IP addresses '
        '(no external IP addresses) to reach the external IP addresses of Google APIs and services.'
    )
