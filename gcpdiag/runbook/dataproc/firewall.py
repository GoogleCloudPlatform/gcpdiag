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
This runbook module checks for issues related to restrictive firewall rules,
which is a common source of networking failures for Dataproc clusters.
"""

from gcpdiag import dataproc
from gcpdiag.queries import apis, crm, dataproc, gce, iam, network

class FirewallRule(runbook.BaseRule):
  """Checks for restrictive firewall rules that could block necessary traffic."""

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
    """Checks for deny-all egress rules that could block traffic."""
    cluster = dataproc.get_cluster(context.project_id, context.region,
                                   context.cluster_name)
    firewall_rules = network.get_firewall_rules_for_cluster(cluster)
    has_deny_all_egress = any(
        rule.is_denied and rule.is_egress and '0.0.0.0/0' in rule.destination_ranges
        for rule in firewall_rules)

    if has_deny_all_egress:
      runbook.add_failed_rule(
          report=runbook.Report(
              short_desc=
              'A restrictive firewall rule may be blocking all egress traffic.',
              long_desc=(
                  'A firewall rule was found in your VPC that denies all egress traffic to the internet (0.0.0.0/0). '
                  'This can prevent your Dataproc cluster from reaching necessary services, '
                  'such as package repositories or Google Cloud APIs.'),
              remediation=(
                  'Please review your firewall rules and ensure that there are higher-priority rules '
                  'that allow necessary egress traffic from your Dataproc cluster.'
              )))
    else:
      runbook.add_ok_rule(
          report=runbook.Report(
              short_desc=
              'No overly restrictive deny-all egress firewall rules were found.'
          ))

  @property
  def solution(self):
    return (
        '**Firewall rules** let you allow or deny traffic to and from your virtual machine (VM) instances based on a configuration that you specify.'
    )
