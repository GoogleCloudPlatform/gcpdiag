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
"""Module containing investigating and resolving GKE logging related issues"""

from typing import Dict

from gcpdiag import runbook
from gcpdiag.lint.gke import util
from gcpdiag.queries import apis, crm, gke, iam, monitoring, quotas
from gcpdiag.runbook import op
from gcpdiag.runbook.gke import flags


class Logs(runbook.DiagnosticTree):
  """Provides a methodical approach to troubleshooting GKE logging issues.

  This runbook guides you through a systematic investigation of potential
  causes when logs from the Google Kubernetes Engine (GKE) cluster are missing
  or incomplete. The focus is on core configuration settings that are essential
  for proper logging functionality.

  The following areas are examined:

  - **Project-Level Logging:** Ensures that the Google Cloud project housing
  the GKE cluster has the Cloud Logging API enabled.

  - **Cluster-Level Logging:** Verifies that logging is explicitly enabled
  within the GKE cluster's configuration.

  - **Node Pool Permissions:** Confirms that the nodes within the cluster's
  node pools have the 'Cloud Logging Write' scope enabled, allowing them to send
  log data.

  - **Service Account Permissions:** Validates that the service account used
  by the node pools possesses the necessary IAM permissions to interact with
  Cloud Logging. Specifically, the "roles/logging.logWriter" role is typically
  required.

  - **Cloud Logging API Write Quotas:** Verifies that Cloud Logging API Write
  quotas have not been exceeded within the specified timeframe.
  """

  parameters = {
      flags.PROJECT_ID: {
          'type': str,
          'help': 'The ID of the project hosting the GKE Cluster',
          'required': True
      },
      flags.NAME: {
          'type':
              str,
          'help':
              '(Optional) The name of the GKE cluster, to limit search only for this cluster',
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
    """Construct the diagnostic tree with appropriate steps."""
    # Instantiate your step classes
    start = LogsStart()
    project_logging_check = LoggingApiEnabled()
    cluster_logging_check = ClusterLevelLoggingEnabled()
    node_pool_access_scope_check = NodePoolCloudLoggingAccessScope()
    service_account_permissions_check = ServiceAccountLoggingPermission()
    logging_write_api_quota_exceeded_check = LoggingWriteApiQuotaExceeded()
    # add them to the tree
    self.add_start(start)
    self.add_step(parent=start, child=project_logging_check)
    self.add_step(parent=project_logging_check, child=cluster_logging_check)
    self.add_step(parent=cluster_logging_check,
                  child=node_pool_access_scope_check)
    self.add_step(parent=node_pool_access_scope_check,
                  child=service_account_permissions_check)
    self.add_step(parent=service_account_permissions_check,
                  child=logging_write_api_quota_exceeded_check)
    self.add_end(step=LogsEnd())


class LogsStart(runbook.StartStep):
  """Initiates diagnostics for GKE Clusters.

  - **Initial Checks:**
    - Verifies if logging API is enabled for the project.
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
    clusters = gke.get_clusters(
        op.get_new_context(project_id=op.get(flags.PROJECT_ID)))
    if not clusters:
      op.add_skipped(
          project_path,
          reason=('No GKE clusters found in project {}').format(project))
      return

    # The following checks adjust based on the input provided:
    # - Both cluster name and location: Verify if that specific cluster exists at that location.

    cluster_name = op.get(flags.NAME)
    cluster_location = op.get(flags.LOCATION)
    found_cluster = False
    found_cluster_with_location = False
    found_clusters_at_location = False
    if cluster_name and cluster_location:
      for cluster in clusters.values():
        if cluster_name == str(cluster).rsplit('/', maxsplit=1)[-1] \
          and cluster_location == str(cluster).split('/')[-3]:
          found_cluster_with_location = True
          break

    if not found_cluster_with_location and cluster_location and cluster_name:
      op.add_skipped(
          project_path,
          reason=('Cluster with the name {} in {} does not exist in project {}'
                 ).format(cluster_name, cluster_location, project))
    # next check includes found_cluster_with_location because we found a cluster at a particular
    # location thus we cannot skip these checks
    elif not found_cluster and not found_cluster_with_location and cluster_name:
      op.add_skipped(
          project_path,
          reason=(
              'Cluster with the name {} does not exist in project {}').format(
                  cluster_name, project))
    elif not found_clusters_at_location and not found_cluster_with_location and cluster_location:
      op.add_skipped(
          project_path,
          reason=('No clusters found at location {} in project {}').format(
              cluster_location, project))


class LoggingApiEnabled(runbook.Step):
  """Verifies if the Cloud Logging API is enabled for the project hosting the GKE cluster.

  This initial step ensures that the fundamental infrastructure for
  logging within the project is operational. If the Cloud Logging API
  is disabled, logs from the GKE cluster won't be collected or stored
  by Google Cloud.
  """

  template = 'logs::project_logging_check'

  def execute(self):
    """Checks if logging API is disabled in the project."""
    project = op.get(flags.PROJECT_ID)
    project_path = crm.get_project(project)

    if apis.is_enabled(project, 'logging'):
      op.add_ok(project_path,
                reason='The logging API is enabled in your project.')
    else:
      op.add_failed(project_path,
                    reason='The logging API is NOT enabled in your project.',
                    remediation='Please endable the logging API')


class ClusterLevelLoggingEnabled(runbook.Step):
  """Verifies that logging is enabled at the GKE cluster level.

  Confirms that the GKE cluster configuration explicitly enables
  logging. Even if the project has the Cloud Logging API enabled
  and other settings are correct, logs won't be collected if
  cluster-level logging is disabled.
  """

  template = 'logs::cluster_logging_check'

  def execute(self):
    """Checks if GKE level logging is disabled"""
    clusters = gke.get_clusters(
        op.get_new_context(project_id=op.get(flags.PROJECT_ID)))
    partial_path = f'{op.get(flags.LOCATION)}/clusters/{op.get(flags.NAME)}'
    cluster_obj = util.get_cluster_object(clusters, partial_path)

    if not cluster_obj.is_autopilot:
      disabled: list[str] = []
      if cluster_obj.has_logging_enabled() and \
        'WORKLOADS' not in cluster_obj.enabled_logging_components():
        disabled.append('workload logs')
      elif not cluster_obj.has_logging_enabled():
        disabled.append('logging')

      if not disabled:
        op.add_ok(
            cluster_obj,
            reason=
            f' GKE level logging is enabled for the cluster {cluster_obj}.')
      else:
        op.add_failed(
            cluster_obj,
            reason=
            f'GKE level logging is not enabled for the cluster {cluster_obj}.',
            remediation='Please endable GKE level logging for this cluster.')


class NodePoolCloudLoggingAccessScope(runbook.Step):
  """Verifies that GKE node pools have the required Cloud Logging access scopes.

  Confirms that the nodes within the GKE cluster's node pools have the necessary
  scopes to write log data to Cloud Logging.  These scopes include
  'https://www.googleapis.com/auth/logging.write' and  potentially others,
  such as 'https://www.googleapis.com/auth/cloud-platform' and
  'https://www.googleapis.com/auth/logging.admin', depending on the configuration.
  """

  template = 'logs::node_pool_access_scope_check'

  def execute(self):
    """Verifies the node pools have Cloud Logging access scope"""

    required_clogging_access_scope = [
        'https://www.googleapis.com/auth/logging.write',
        'https://www.googleapis.com/auth/cloud-platform',
        'https://www.googleapis.com/auth/logging.admin'
    ]

    clusters = gke.get_clusters(
        op.get_new_context(project_id=op.get(flags.PROJECT_ID)))
    partial_path = f'{op.get(flags.LOCATION)}/clusters/{op.get(flags.NAME)}'
    cluster_obj = util.get_cluster_object(clusters, partial_path)

    for nodepool in cluster_obj.nodepools:

      if any(s in nodepool.config.oauth_scopes
             for s in required_clogging_access_scope):
        op.add_ok(
            nodepool,
            reason=
            f'The node pool {nodepool} has the correct Cloud Logging access scope.'
        )
      else:
        op.add_failed(
            nodepool,
            reason=
            f'The node pool {nodepool} is missing Cloud Logging access scope.',
            remediation=
            'Please create new node pools with the correct logging scope. \
          Please read https://cloud.google.com/kubernetes-engine/docs/troubleshooting/logging\
#verify_nodes_in_the_node_pools_have_access_scope.')


class ServiceAccountLoggingPermission(runbook.Step):
  """Verifies the service accounts associated with node pools have 'logging.logWriter' permissions.

  Checks that the service accounts used by nodes in the GKE cluster
  have the essential "roles/logging.logWriter" IAM permission. This
  permission is required to send log data to Google Cloud Logging.
  """

  template = 'logs::service_account_permissions_check'

  def execute(self):
    """
    Verifies the node pool's service account has a role with the correct logging IAM permissions
    """
    clusters = gke.get_clusters(
        op.get_new_context(project_id=op.get(flags.PROJECT_ID)))
    partial_path = f'{op.get(flags.LOCATION)}/clusters/{op.get(flags.NAME)}'
    cluster_obj = util.get_cluster_object(clusters, partial_path)
    iam_policy = iam.get_project_policy(op.get(flags.PROJECT_ID))

    logging_role = 'roles/logging.logWriter'

    # Verifies service-account permissions for every nodepool.
    for np in cluster_obj.nodepools:
      sa = np.service_account
      if not iam.is_service_account_enabled(sa, op.get(flags.PROJECT_ID)):
        op.add_failed(
            np,
            reason=f'The service account {sa} is disabled or deleted.',
            remediation='The service account {} used by GKE nodes should have \
                      the logging.logWriter role.'.format(sa))
      elif not iam_policy.has_role_permissions(f'serviceAccount:{sa}',
                                               logging_role):
        op.add_failed(np,
                      reason='The service account: {} is missing \
role: {}.'.format(sa, logging_role),
                      remediation='Please grant the role: {} to the service \
account: {}.'.format(logging_role, sa))
      else:
        op.add_ok(np,
                  reason='Service account: {} has the correct \
logging permissions.'.format(sa))


class LoggingWriteApiQuotaExceeded(runbook.Step):
  """Verifies that Cloud Logging API write quotas have not been exceeded.

  Checks if the project has exceeded any Cloud Logging write quotas within
  the defined timeframe. Exceeding the quota could prevent nodes from sending
  log data, even if other configurations are correct.
  """

  template = 'logs::logging_write_api_quota_exceeded_check'

  def execute(self):
    """Checks if Cloud Logging API write quotas have been exceeded"""

    query_results_per_project_id: Dict[str,
                                       monitoring.TimeSeriesCollection] = {}

    params = {
        'start_time':
            op.get(flags.START_TIME).strftime("d\'%Y/%m/%d-%H:%M:%S'"),
        'end_time':
            op.get(flags.END_TIME).strftime("d\'%Y/%m/%d-%H:%M:%S'")
    }

    query_results_per_project_id[op.get(flags.PROJECT_ID)] = \
        monitoring.query(
            op.get(flags.PROJECT_ID),
            quotas.QUOTA_EXCEEDED_QUERY_WINDOW_TEMPLATE.format_map(params))

    project = op.get(flags.PROJECT_ID)
    project_path = crm.get_project(project)

    if len(query_results_per_project_id[project]) == 0:
      op.add_ok(project_path,
                reason=op.prep_msg(op.SUCCESS_REASON,
                                   start_time=op.get(flags.START_TIME),
                                   end_time=op.get(flags.END_TIME)))
    else:
      exceeded_quotas = []
      for i in query_results_per_project_id[project].values():
        if i['labels'][
            'metric.limit_name'] == 'WriteRequestsPerMinutePerProject':
          try:
            exceeded_quotas.append(i['labels']['metric.limit_name'])
          except KeyError:
            op.add_skipped(op.project, 'no data')
            #invalid query result
            return
      exceeded_quota_names = ', '.join(exceeded_quotas)
      op.add_failed(
          project_path,
          reason='Project {} has recently exceeded the following \
quotas: {}.'.format(project, exceeded_quota_names),
          remediation='Please check the project {} for the Cloud Logging API \
quotas {} which have been reached'.format(project, exceeded_quota_names))


class LogsEnd(runbook.EndStep):
  """Finalizes the 'GKE logs' diagnostic process.

  Prompts the user for satisfaction with the Root Cause Analysis (RCA) and takes appropriate
  actions based on their response:

  * **Confirmation:** Concludes the runbook execution.
  * **Further Action:** Triggers additional steps, such as report generation, if necessary.
  """

  def execute(self):
    """Finalize `GKE logs` diagnostics."""
    response = op.prompt(
        kind=op.CONFIRMATION,
        message='Are you satisfied with the `GKE logs` RCA performed?')
    if response == op.NO:
      op.info(message=op.END_MESSAGE)
      op.interface.rm.generate_report()
