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
"""Module containing investigating and resolving GKE Monitoring related issues"""

from gcpdiag import runbook
from gcpdiag.lint.gke import util
from gcpdiag.queries import crm, gke
from gcpdiag.runbook import op
from gcpdiag.runbook.gke import flags
from gcpdiag.runbook.gke import generalized_steps as gke_gs


class MonitoringConfiguration(runbook.DiagnosticTree):
  """Verifies that GKE Monitoring and its components are correctly configured and operational.

  This runbook guides through a systematic investigation of potential
  causes when monitoring from the Google Kubernetes Engine (GKE) cluster are missing
  or incomplete. The focus is on core configuration settings that are essential
  for proper monitoring functionality.

  The following areas are examined:

  - **Project-Level Monitoring:** Ensures that the Google Cloud project housing
  the GKE cluster has the Cloud Monitoring API enabled.

  - **Cluster-Level Monitoring:** Verifies that monitoring is explicitly enabled
  within the GKE cluster's configuration.

  - **Node Pool Permissions:** Confirms that the nodes within the cluster's
  node pools have the 'Cloud Monitoring Write' scope enabled, allowing them to send
  metrics data.

  - **Service Account Permissions:** Validates that the service account used
  by the node pools possesses the necessary IAM permissions to interact with
  Cloud Monitoring. Specifically, the "roles/monitoring.metricWriter" role is typically
  required.

  """

  parameters = {
      flags.PROJECT_ID: {
          'type': str,
          'help': 'The ID of the project hosting the GKE Cluster',
          'required': True
      },
      flags.GKE_CLUSTER_NAME: {
          'type':
              str,
          'help':
              'The name of the GKE cluster, to limit search only for this cluster',
          'required':
              True
      },
      flags.LOCATION: {
          'type': str,
          'help': 'The zone or region of the GKE cluster',
          'required': True
      }
  }

  def build_tree(self):
    """Constructs the diagnostic tree with appropriate steps."""
    # Instantiate the step classes
    start = MonitoringConfigurationStart()
    project_monitoring_configuration_check = MonitoringApiConfigurationEnabled()
    cluster_monitoring_configuration_check = ClusterLevelMonitoringConfigurationEnabled(
    )
    node_pool_access_scope_configuration_check = NodePoolCloudMonitoringAccessScopeConfiguration(
    )
    service_account_permissions_check = ServiceAccountMonitoringPermissionConfiguration(
    )

    # add them to the tree
    self.add_start(start)
    self.add_step(parent=start, child=project_monitoring_configuration_check)
    self.add_step(parent=project_monitoring_configuration_check,
                  child=cluster_monitoring_configuration_check)
    self.add_step(parent=cluster_monitoring_configuration_check,
                  child=node_pool_access_scope_configuration_check)
    self.add_step(parent=node_pool_access_scope_configuration_check,
                  child=service_account_permissions_check)
    self.add_end(step=MonitoringConfigurationEnd())


class MonitoringConfigurationStart(runbook.StartStep):
  """Initiates diagnostics for GKE Clusters.

  - **Initial Checks:**
    - Verifies if Monitoring API is enabled for the project.
    - Validates that there are GKE clusters in the project.
    - (Optional) If a cluster name is provided, checks if that cluster exists in the project.
    - (Optional) If a location is provided, verifies there are clusters in that location.
    - (Optional) If both a location and a name are provided, verifies that the cluster
    exists at that location.
  """

  def execute(self):
    """Checks the provided parameters."""
    project = op.get(flags.PROJECT_ID)
    project_path = crm.get_project(project)

    # Checks if there are clusters in the project
    clusters = gke.get_clusters(op.get_context())
    if not clusters:
      op.add_skipped(
          project_path,
          reason=('No GKE clusters found in project {}').format(project))
      return

    # The following checks adjust based on the input provided:
    # - Both cluster name and location: Verify if that specific cluster exists at that location.

    cluster_name = op.get(flags.GKE_CLUSTER_NAME)
    cluster_location = op.get(flags.LOCATION)

    # Initialize flags to track findings
    found_cluster = False
    found_cluster_with_location = False
    found_clusters_at_location = False

    if cluster_name or cluster_location:
      for cluster in clusters.values():
        name_match = cluster_name and (cluster_name == str(cluster).rsplit(
            '/', 1)[-1])
        location_match = cluster_location and (cluster_location
                                               == str(cluster).split('/')[-3])

        if name_match:
          found_cluster = True
        if location_match:
          found_clusters_at_location = True
        if name_match and location_match:
          found_cluster_with_location = True
          break  # After finding the exact required, no need to search further

    # Checking the matching conditions for the required cluster in Order
    if not found_cluster_with_location and cluster_name and cluster_location:
      op.add_skipped(
          project_path,
          reason=('Cluster with the name {} in {} does not exist in project {}'
                 ).format(cluster_name, cluster_location, project))
    elif not found_cluster and cluster_name:
      op.add_skipped(
          project_path,
          reason=(
              'Cluster with the name {} does not exist in project {}').format(
                  cluster_name, project))
    elif not found_clusters_at_location and cluster_location:
      op.add_skipped(
          project_path,
          reason=('No clusters found at location {} in project {}').format(
              cluster_location, project))


class MonitoringApiConfigurationEnabled(gke_gs.ApiEnabled):
  """Verifies if the Cloud Monitoring API is enabled for the project.

  This initial step ensures that the fundamental infrastructure for
  monitoring within the project is operational. If the Cloud Monitoring API
  is disabled, monitoring from the GKE cluster won't be collected or stored
  by Google Cloud.
  """

  api_name = 'monitoring'
  template = 'monitoring_configuration::project_monitoring_configuration_check'


class ClusterLevelMonitoringConfigurationEnabled(runbook.Step):
  """Verifies that monitoring is enabled at the GKE cluster level.

  Confirms that the GKE cluster configuration explicitly enables
  monitoring. Even if the project has the Cloud Monitoring API enabled
  and other settings are correct, monitoring won't be collected if
  cluster-level monitoring is disabled .
  """

  template = 'monitoring_configuration::cluster_monitoring_configuration_check'

  def execute(self):
    """Checks if GKE level Monitoring is disabled."""
    clusters = gke.get_clusters(op.get_context())
    partial_path = f'{op.get(flags.LOCATION)}/clusters/{op.get(flags.GKE_CLUSTER_NAME)}'
    cluster_obj = util.get_cluster_object(clusters, partial_path)

    # Available GKE cluster metrics as of 28 April 2025
    gke_monitoring_components = {
        'CADVISOR', 'DAEMONSET', 'DEPLOYMENT', 'HPA', 'KUBELET', 'POD',
        'STATEFULSET', 'STORAGE', 'SYSTEM_COMPONENTS'
    }
    #'APISERVER', 'CONTROLLER_MANAGER, 'SCHEDULER' => ControlPlane components
    # monitoring are not enabled by default due to which skipping its check

    if not cluster_obj.is_autopilot:
      disabled = []

      if cluster_obj.has_monitoring_enabled():

        # Enabled metrics on the provided cluster
        cluster_enabled_monitoring_metrics = cluster_obj.enabled_monitoring_components(
        )

        # Check if the cluster has GPU based Nodepool
        # Find any GPU node pools by taint
        for np in cluster_obj.nodepools:  #Iterate our all available NodePool
          # pylint: disable=protected-access
          config_data = np._resource_data.get('config', {})
          taints = config_data.get('taints', [])

          for t in taints:  #Iterate our the taints on the Nodepool
            if (t.get('key') == 'nvidia.com/gpu' and
                t.get('value') == 'present' and
                t.get('effect') == 'NO_SCHEDULE'):

              gke_monitoring_components.add('DCGM')

              break  #if found first occurrence then break

        # Check missing metrics
        not_enabled_cluster_metrics = gke_monitoring_components - set(
            cluster_enabled_monitoring_metrics)

        if not_enabled_cluster_metrics:
          not_enabled_cluster_metrics_string = ', '.join(
              sorted(not_enabled_cluster_metrics))
          disabled.append(
              f'Missing metrics: {not_enabled_cluster_metrics_string}')
      else:
        disabled.append('Monitoring entirely disabled')

      if not disabled:
        op.add_ok(
            cluster_obj,
            reason=
            f'GKE level monitoring is fully enabled for the cluster {cluster_obj}.'
        )
      else:
        disabled_components_metrics = ', '.join(disabled)
        op.add_failed(
            cluster_obj,
            reason=
            f'GKE level monitoring is not fully enabled for the cluster {cluster_obj}.',
            remediation=(
                f'Issues detected:\n    {disabled_components_metrics}.\n'
                f'Please enable missing components or full GKE monitoring.'))


class NodePoolCloudMonitoringAccessScopeConfiguration(gke_gs.NodePoolScope):
  """Verifies that GKE node pools have the required Cloud Monitoring access scopes.

  Confirms that the nodes within the GKE cluster's node pools have the necessary
  scopes to write metrics data to Cloud Monitoring.  These scopes include
  'https://www.googleapis.com/auth/monitoring' and potentially others,
  such as 'https://www.googleapis.com/auth/cloud-platform' and
  'https://www.googleapis.com/auth/monitoring.write', depending on the configuration.
  """

  template = 'monitoring_configuration::node_pool_access_scope_configuration_check'
  required_scopes = [
      'https://www.googleapis.com/auth/monitoring',
      'https://www.googleapis.com/auth/monitoring.write',
      'https://www.googleapis.com/auth/cloud-platform'
  ]
  service_name = 'Monitoring'


class ServiceAccountMonitoringPermissionConfiguration(
    gke_gs.ServiceAccountPermission):
  """Verifies that service accounts in GKE node pools have monitoring permissions.

  Checks that the service accounts used by nodes in the GKE cluster
  have the essential "roles/monitoring.metricWriter" IAM permission. This
  permission is required to send metric data to Google Cloud Monitoring.
  """

  template = 'monitoring_configuration::service_account_permissions_configuration_check'
  required_roles = [
      'roles/monitoring.metricWriter',
      'roles/stackdriver.resourceMetadata.writer'
  ]
  service_name = 'monitoring'


class MonitoringConfigurationEnd(runbook.EndStep):
  """Finalizes diagnostics for GKE Monitoring.

  Prompts the user for satisfaction with the Root Cause Analysis (RCA)
  and takes appropriate actions based on their response:

  * **Confirmation:** Concludes the runbook execution.
  * **Further Action:** Triggers additional steps, such as report generation, if necessary.
  """

  def execute(self):
    """Finalizes `GKE Monitoring` diagnostics."""
    response = op.prompt(
        kind=op.CONFIRMATION,
        message='Are you satisfied with the `GKE Monitoring` RCA performed?')
    if response == op.NO:
      op.info(message=op.END_MESSAGE)
