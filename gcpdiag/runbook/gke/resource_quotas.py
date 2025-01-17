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

import re
from datetime import datetime

from gcpdiag import runbook
from gcpdiag.queries import crm, gke, logs
from gcpdiag.runbook import op
from gcpdiag.runbook.gcp import generalized_steps as gcp_gs
from gcpdiag.runbook.gke import flags
from gcpdiag.utils import Version


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
          'required': True
      },
      flags.NAME: {
          'type':
              str,
          'help':
              '(Optional) The name of the GKE cluster, to limit search only for this cluster',
          'required':
              False
      },
      flags.LOCATION: {
          'type': str,
          'help': '(Optional) The zone or region of the GKE cluster',
          'required': False
      },
      flags.START_TIME_UTC: {
          'type':
              datetime,
          'help':
              '(Optional) The start window to query the logs. Format: YYYY-MM-DDTHH:MM:SSZ',
          'required':
              False
      },
      flags.END_TIME_UTC: {
          'type':
              datetime,
          'help':
              '(Optional) The end window for the logs. Format: YYYY-MM-DDTHH:MM:SSZ',
          'required':
              False
      }
  }

  def build_tree(self):

    start = ResourceQuotasStart()
    project_logging_check = gcp_gs.ServiceApiStatusCheck()
    project_logging_check.api_name = 'logging'
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
    project = op.get(flags.PROJECT_ID)
    project_path = crm.get_project(project)
    cluster_name = op.get(flags.NAME)
    cluster_location = op.get(flags.LOCATION)

    if cluster_location:
      op.context.locations_pattern = re.compile(cluster_location)
    if cluster_name:
      op.context.resources_pattern = re.compile(cluster_name)

    # check if there are clusters in the project
    # following checks are necessary, depending on what input is provided:
    # - no input, get all clusters available
    # - just cluster name is provided, check if there's a cluster with that name
    # - just location is provided, check if there are clusters at that location
    # - cluster name and location are provided, check if there's that cluster at that location
    clusters = gke.get_clusters(op.context)
    if not clusters:
      reason = f'No GKE clusters found in project {project}'
      remediation = 'Please verify the provided GKE cluster project id'
      if cluster_location and cluster_name:
        reason = f'No {cluster_name} cluster found at {cluster_location} in project {project}.'
        remediation = 'Please verify the provided GKE cluster name and location'
      elif cluster_location:
        reason = f'No clusters found at location {cluster_location} in project {project}'
        remediation = 'Please verify the provided GKE cluster location'
      elif cluster_name:
        reason = f'Cluster with the name {cluster_name} does not exist in project {project}'
        remediation = 'Please verify the provided GKE cluster name'

      op.add_failed(project_path, reason=reason, remediation=remediation)


class ClusterVersion(runbook.Step):
  """Check for cluster version"""
  GKE_QUOTA_ENFORCEMENT_MIN_VERSION = Version('1.28.0')

  def execute(self):
    """
    Verify clusters running version. GKE doesn't enforce the Kubernetes
    resource quotas for clusters running version 1.28 or later.
    """
    clusters = gke.get_clusters(op.context)
    for cluster in clusters.values():
      resource_quota_exceeded = ResourceQuotaExceeded()
      resource_quota_exceeded.cluster_name = cluster.name
      resource_quota_exceeded.cluster_location = cluster.location

      if cluster.master_version >= self.GKE_QUOTA_ENFORCEMENT_MIN_VERSION:
        resource_quota_exceeded.template = 'resourcequotas::higher_version_quota_exceeded'
      else:
        resource_quota_exceeded.template = 'resourcequotas::lower_version_quota_exceeded'
      self.add_child(resource_quota_exceeded)


class ResourceQuotaExceeded(runbook.Step):
  """Verifies that Kubernetes resource quotas have been exceeded or not.
  """
  cluster_name: str
  cluster_location: str
  template: str = 'resourcequotas::lower_version_quota_exceeded'

  def execute(self):
    """
    Verifies that Kubernetes resource quotas have been exceeded or not.

    If value for "start_time_utc" and "end_time_utc" are not provided as parameter
    then this step will check the logs for last 8 hours.
    Check if there is any "forbidden: exceeded quota" log entries.
    """

    project = op.get(flags.PROJECT_ID)
    project_path = crm.get_project(project)
    error_message = 'protoPayload.status.message:"forbidden: exceeded quota"'
    filter_str = f'resource.labels.location="{self.cluster_location}" \
      resource.labels.cluster_name="{self.cluster_name}" {error_message}'

    log_entries = logs.realtime_query(project_id=project,
                                      filter_str=filter_str,
                                      start_time_utc=op.get(
                                          flags.START_TIME_UTC),
                                      end_time_utc=op.get(flags.END_TIME_UTC))

    if log_entries:
      # taking the last log entry to provide as output, because the latest log entry is always
      # more relevant than the 1st
      sample_log = 'No message' or log_entries[-1]['protoPayload']['status'][
          'message']
      op.add_failed(project_path,
                    reason=op.prep_msg(op.FAILURE_REASON,
                                       LOG_ENTRY=sample_log,
                                       CLUSTER=self.cluster_name,
                                       PROJECT=project,
                                       LOCATION=self.cluster_location,
                                       START_TIME_UTC=op.get(
                                           flags.START_TIME_UTC),
                                       END_TIME_UTC=op.get(flags.END_TIME_UTC)),
                    remediation=op.prep_msg(op.FAILURE_REMEDIATION))
    else:
      op.add_ok(project_path,
                reason=op.prep_msg(op.SUCCESS_REASON,
                                   CLUSTER=self.cluster_name,
                                   PROJECT=project,
                                   LOCATION=self.cluster_location,
                                   START_TIME_UTC=op.get(flags.START_TIME_UTC),
                                   END_TIME_UTC=op.get(flags.END_TIME_UTC)))


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
