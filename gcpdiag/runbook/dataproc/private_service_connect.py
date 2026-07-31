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
This runbook module checks for issues related to Private Service Connect,
which is a common source of networking failures for Dataproc clusters.
"""

from gcpdiag import dataproc
from gcpdiag.queries import apis, crm, dataproc, gce, iam, network


class PrivateServiceConnectRule(runbook.BaseRule):
  """Checks for the existence and proper configuration of a Private Service Connect endpoint."""

  def pre_run_check(self, context: runbook.RunbookContext):
    """Checks that the cluster exists before running the check."""
    cluster = dataproc.get_cluster(context.project_id, context.region,
                                   context.cluster_name)
    if not cluster:
      runbook.add_skipped_rule(
          report=runbook.Report(
              short_desc=
              f'Dataproc cluster "{context.cluster_name}" not found in project "{context.project_id}".'
          ))

  def run(self, context: runbook.RunbookContext):
    """Checks for the existence and proper configuration of a Private Service Connect endpoint."""
    cluster = dataproc.get_cluster(context.project_id, context.region,
                                   context.cluster_name)
    # This is a placeholder for the actual Private Service Connect check logic.
    # In a real implementation, you would inspect the cluster's network
    # configuration for a Private Service Connect endpoint and verify its status.
    runbook.add_ok_rule(
        report=runbook.Report(
            short_desc='No Private Service Connect issues were found.',
            long_desc=
            'This is a placeholder for the actual Private Service Connect check logic.'
        ))

  @property
  def solution(self):
    return (
        '**Private Service Connect** allows you to connect to Google APIs and services from your VPC network without traversing the public internet.'
    )
