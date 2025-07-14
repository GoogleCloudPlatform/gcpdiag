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
"""GKE Resource Quotas runbook"""

from datetime import datetime

from boltons.iterutils import get_path

from gcpdiag import runbook
from gcpdiag.queries import crm, gke, logs
from gcpdiag.runbook import op
from gcpdiag.runbook.gcp import generalized_steps as gcp_gs
from gcpdiag.runbook.gke import flags
from gcpdiag.utils import GcpApiError, Version


class ResourceQuotas(runbook.DiagnosticTree):
  """Analyses logs in the project where the cluster is running.

  If there are log entries that contain messages listed in the public documentation
  https://cloud.google.com/knowledge/kb/google-kubernetes-engine-pods-fail-to-start-due-to-exceeded-quota-000004701
  then provide details on how this issue can be solved.
  """

  # Specify parameters common to all steps in the diagnostic tree class.
  parameters = {
      flags.PROJECT_ID: {
          'type': str,
          'help': 'The Project ID of the resource under investigation',
          'required': True,
      },
      flags.NAME: {
          'type': str,
          'help': ('The name of the GKE cluster, to limit search only for this'
                   ' cluster'),
          'deprecated': True,
          'new_parameter': 'gke_cluster_name',
      },
      flags.GKE_CLUSTER_NAME: {
          'type': str,
          'help': ('The name of the GKE cluster, to limit search only for'
                   ' this cluster'),
          'required': True,
      },
      flags.LOCATION: {
          'type': str,
          'help': '(Optional) The zone or region of the GKE cluster',
          'required': True,
      },
      flags.START_TIME: {
          'type': datetime,
          'help': ('(Optional) The start window to query the logs. Format:'
                   ' YYYY-MM-DDTHH:MM:SSZ'),
          'required': False,
      },
      flags.END_TIME: {
          'type': datetime,
          'help': ('(Optional) The end window for the logs. Format:'
                   ' YYYY-MM-DDTHH:MM:SSZ'),
          'required': False,
      },
  }

  def legacy_parameter_handler(self, parameters):
    if flags.NAME in parameters:
      parameters[flags.GKE_CLUSTER_NAME] = parameters.pop(flags.NAME)

  def build_tree(self):

    start = ResourceQuotasStart()
    project_logging_check = gcp_gs.ServiceApiStatusCheck()
    project_logging_check.api_name = 'logging'
    project_logging_check.project_id = op.get(flags.PROJECT_ID)
    project_logging_check.expected_state = gcp_gs.constants.APIState.ENABLED

    clusterversion = ClusterVersion()
    end = ResourceQuotasEnd()

    self.add_start(step=start)
    self.add_step(parent=start, child=project_logging_check)
    self.add_step(parent=project_logging_check, child=clusterversion)
    self.add_end(step=end)


class ResourceQuotasStart(runbook.StartStep):
  """Initiates diagnostics for Resource Quotas.

  Check
  - if logging API is enabled
  - if there are GKE clusters in the project
  - if a cluster name is provided, verify if that cluster exists in the project
  - if a location is provided, verify there are clusters in that location
  - if both a location and a name are provided, verify that the cluster exists at that location
  """

  def execute(self):
    """
    Check the provided parameters.
    """
    project = crm.get_project(op.get(flags.PROJECT_ID))
    try:
      cluster = gke.get_cluster(op.get(flags.PROJECT_ID),
                                cluster_id=op.get(flags.GKE_CLUSTER_NAME),
                                location=op.get(flags.LOCATION))
    except GcpApiError:
      op.add_skipped(
          project,
          reason=('Cluster {} does not exist in {} for project {}').format(
              op.get(flags.GKE_CLUSTER_NAME), op.get(flags.LOCATION),
              op.get(flags.PROJECT_ID)))
    else:
      op.add_ok(project,
                reason=('Cluster {} found in {} for project {}').format(
                    cluster.name, op.get(flags.LOCATION),
                    op.get(flags.PROJECT_ID)))


class ClusterVersion(runbook.Step):
  """Check for cluster version"""
  GKE_QUOTA_ENFORCEMENT_MIN_VERSION = Version('1.28.0')

  def execute(self):
    """
    Verify cluster's running version. GKE doesn't enforce the Kubernetes
    resource quotas for clusters running version 1.28 or later.
    """
    cluster = gke.get_cluster(op.get(flags.PROJECT_ID),
                              cluster_id=op.get(flags.GKE_CLUSTER_NAME),
                              location=op.get(flags.LOCATION))
    resource_quota_exceeded = ResourceQuotaExceeded()
    resource_quota_exceeded.cluster_name = cluster.name
    resource_quota_exceeded.project_id = op.get(flags.PROJECT_ID)
    resource_quota_exceeded.cluster_location = cluster.location

    if cluster.master_version >= self.GKE_QUOTA_ENFORCEMENT_MIN_VERSION:
      resource_quota_exceeded.template = 'resourcequotas::higher_version_quota_exceeded'
    else:
      resource_quota_exceeded.template = 'resourcequotas::lower_version_quota_exceeded'
    self.add_child(resource_quota_exceeded)


class ResourceQuotaExceeded(runbook.Step):
  """Verify that Kubernetes resource quotas have not been exceeded."""
  cluster_name: str
  cluster_location: str
  project_id: str
  template: str = 'resourcequotas::lower_version_quota_exceeded'

  def execute(self):
    """Verify that Kubernetes resource quotas for cluster

    project/{project_id}/locations/{cluster_location}/clusters/{cluster_name} were not
    exceeded between {start_time} and {end_time}
    """

    project = crm.get_project(self.project_id)
    filter_list = [
        'log_id("cloudaudit.googleapis.com/activity")',
        'resource.type="k8s_cluster"',
        f'resource.labels.location="{self.cluster_location}"',
        f'resource.labels.cluster_name="{self.cluster_name}"',
        'protoPayload.status.message:"forbidden: exceeded quota"'
    ]

    filter_str = '\n'.join(filter_list)

    log_entries = logs.realtime_query(project_id=project.project_id,
                                      filter_str=filter_str,
                                      start_time=op.get(flags.START_TIME),
                                      end_time=op.get(flags.END_TIME))

    if log_entries:
      # taking the last log entry to provide as output, because the latest log entry is always
      # more relevant than the 1st

      json_payload = get_path(log_entries[-1], ('protoPayload', 'status'),
                              default={})
      sample_log = f"Log Message: {json_payload.get('message', 'N/A')}"

      op.add_failed(project,
                    reason=op.prep_msg(op.FAILURE_REASON,
                                       log_entry=sample_log,
                                       cluster=self.cluster_name,
                                       project=project,
                                       location=self.cluster_location,
                                       start_time=op.get(flags.START_TIME),
                                       end_time=op.get(flags.END_TIME)),
                    remediation=op.prep_msg(op.FAILURE_REMEDIATION))
    else:
      op.add_ok(project,
                reason=op.prep_msg(op.SUCCESS_REASON,
                                   cluster=self.cluster_name,
                                   project=project,
                                   location=self.cluster_location,
                                   start_time=op.get(flags.START_TIME),
                                   end_time=op.get(flags.END_TIME)))


class ResourceQuotasEnd(runbook.EndStep):
  """Finalizes the diagnostics process for `Resource Quotas`.

  This step prompts the user to confirm satisfaction with the Root Cause Analysis (RCA)
  performed for `Resource Quotas`.

  Depending on the user's response, it may conclude the runbook execution or trigger additional
  steps, such as generating a report of the findings.
  """

  def execute(self):
    """Finalize `Resource Quotas` diagnostics."""
    response = op.prompt(
        kind=op.CONFIRMATION,
        message='Are you satisfied with the `GKE Resource Quotas` RCA performed?'
    )
    if response == op.NO:
      op.info(message=op.END_MESSAGE)
