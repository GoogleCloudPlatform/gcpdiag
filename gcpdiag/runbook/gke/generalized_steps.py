# Copyright 2024 Google LLC
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
"""Contains Generalized steps used by only GKE runbooks"""

from gcpdiag import runbook
from gcpdiag.lint.gke import util
from gcpdiag.queries import apis, crm, gke, iam
from gcpdiag.runbook import op
from gcpdiag.runbook.gke import flags


class ApiEnabled(runbook.Step):
  """Step to verify if a given Google Cloud API is enabled for the project.

    Attributes:
      api_name (str): the API service name (e.g. 'monitoring', 'logging').
      template (str): the runbook template path for this check.
    """
  api_name: str
  template: str

  def execute(self):
    """Verify if the API is enabled for this project."""

    project = op.get(flags.PROJECT_ID)
    project_path = crm.get_project(project)

    if apis.is_enabled(project, self.api_name):
      op.add_ok(project_path, reason=f'The {self.api_name} API is enabled.')
    else:
      op.add_failed(project_path,
                    reason=f'The {self.api_name} API is NOT enabled.',
                    remediation=f'Please enable the {self.api_name} API')


class NodePoolScope(runbook.Step):
  """Step to verify that each GKE node pool has at least one of the required OAuth scopes.

    Attributes:
      required_scopes (list): a list of OAuth scope URLs to check.
      template (str): the runbook template path for this check.
      service_name (str) the service whose role need to be check.
    """

  required_scopes: list
  template: str
  service_name: str

  def execute(self):
    """Verify node-pool OAuth scopes include one of the required scopes."""
    # fetch all clusters
    clusters = gke.get_clusters(op.get_context())
    # find target cluster by name and location
    partial = f"{op.get(flags.LOCATION)}/clusters/{op.get(flags.GKE_CLUSTER_NAME)}"
    cluster_obj = util.get_cluster_object(clusters, partial)

    for nodepool in cluster_obj.nodepools:
      if any(s in nodepool.config.oauth_scopes for s in self.required_scopes):
        op.add_ok(
            nodepool,
            reason=
            f'The node pool {nodepool} has the correct {self.service_name} access scope.'
        )
      else:
        op.add_failed(
            nodepool,
            reason=
            f'The node pool {nodepool} is missing {self.service_name} access scope.',
            remediation=
            f'Please create new node pools with the correct {self.service_name} scope.'
        )


class ServiceAccountPermission(runbook.Step):
  """Step to verify that service accounts in GKE node pools have the required IAM roles.

    Attributes:
      required_roles (list): list of IAM roles to check on each node-pool service account.
      template (str): the runbook template path for this check.
      service_name (str) the service for which service account permissions need to be check.
    """
  required_roles: list
  template: str
  service_name: str

  def execute(self):
    """Verifies the node pool's service account has a role with the correct
    required service IAM permissions."""

    clusters = gke.get_clusters(op.get_context())
    partial_path = f'{op.get(flags.LOCATION)}/clusters/{op.get(flags.GKE_CLUSTER_NAME)}'
    cluster_obj = util.get_cluster_object(clusters, partial_path)
    iam_policy = iam.get_project_policy(op.get_context())

    # Verifies service-account permissions for every nodepool.
    for np in cluster_obj.nodepools:
      sa = np.service_account
      if not iam.is_service_account_enabled(sa, op.get_context()):
        op.add_failed(
            np,
            reason=f'The service account {sa} is disabled or deleted.',
            remediation=(
                f'The service account {sa} used by GKE nodes should have '
                f'the required {self.service_name} role.'))

      #checking all roles for ServiceAccount of all Nodepool
      missing_roles = []
      for role in self.required_roles:
        if not iam_policy.has_role_permissions(f'serviceAccount:{sa}', role):
          missing_roles.append(role)

      missing_roles_string = ', '.join(missing_roles)

      if missing_roles:
        op.add_failed(
            np,
            reason=
            (f'The service account: {sa} is missing role(s): {missing_roles_string}.'
            ),
            remediation=
            (f'Please grant the role(s): {missing_roles_string} to the service account: {sa}.'
            ))
      else:
        op.add_ok(np,
                  reason=(f'Service account: {sa} has the correct '
                          f'{self.service_name} permissions.'))
