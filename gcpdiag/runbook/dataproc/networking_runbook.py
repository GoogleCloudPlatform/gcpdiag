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
This is the main runbook for diagnosing Dataproc networking and permission issues.
It serves as a "Diagnostic Tree" that orchestrates a series of individual
checks (steps) to identify the root cause of a problem.
"""

from gcpdiag import dataproc
from gcpdiag.runbook.dataproc import flags
from gcpdiag.runbook.dataproc.steps import (
    cluster_existence,
    cloud_nat,
    pga,
    firewall,
    iam,
)

class NetworkingRunbook(runbook.DiagnosticTree):
  """Dataproc Networking and Permissions Runbook"""

  parameters = {
      flags.PROJECT_ID: {
          'type': str,
          'required': True,
          'help': 'The project ID of the Dataproc cluster'
      },
      flags.DATAPROC_CLUSTER_NAME: {
          'type': str,
          'required': True,
          'help': 'The name of the Dataproc cluster to inspect'
      },
      flags.REGION: {
          'type': str,
          'required': True,
          'help': 'The region of the Dataproc cluster'
      },
  }

  def build_tree(self):
    """
        This method defines the logical flow of the diagnostic checks.
        It links the individual steps together to form a decision tree.
        """
    # The runbook starts with a single, clear entry point.
    start = runbook.StartStep()
    self.add_start(start)

    # The first step is to verify that the cluster actually exists.
    # If it doesn't, there's no point in running the other checks.
    check_cluster_exists = cluster_existence.ClusterExistenceStep()
    self.add_step(parent=start, child=check_cluster_exists)

    # If the cluster exists, we can proceed with the individual checks.
    # We'll run them in a logical order, starting with the most common
    # issues.
    check_pga = pga.PrivateGoogleAccessStep()
    self.add_step(parent=check_cluster_exists, child=check_pga)

    check_cloud_nat = cloud_nat.CloudNatStep()
    self.add_step(parent=check_pga, child=check_cloud_nat)

    check_firewall = firewall.FirewallStep()
    self.add_step(parent=check_cloud_nat, child=check_firewall)

    check_iam = iam.IamStep()
    self.add_step(parent=check_firewall, child=check_iam)

    # The runbook ends with a single, clear exit point.
    self.add_end(runbook.EndStep())
