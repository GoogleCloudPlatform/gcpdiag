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
"""GKE Image pull failures runbook"""

from datetime import datetime

from boltons.iterutils import get_path

from gcpdiag import runbook
from gcpdiag.queries import apis, crm, gke, logs
from gcpdiag.runbook import op
from gcpdiag.runbook.gke import flags


def local_realtime_query(filter_list):
  filter_str = '\n'.join(filter_list)
  result = logs.realtime_query(project_id=op.get(flags.PROJECT_ID),
                               start_time_utc=op.get(flags.START_TIME_UTC),
                               end_time_utc=op.get(flags.END_TIME_UTC),
                               filter_str=filter_str)
  return result


class ImagePull(runbook.DiagnosticTree):
  """Analysis and Resolution of Image Pull Failures on GKE clusters.

  This runbook investigates the gke cluster for Image pull failures and recommends remediation
  steps.

  Areas Examined:

  - GKE cluster

  - Stackdriver logs
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
    """Construct the diagnostic tree with appropriate steps."""
    # Instantiate your step classes
    start = ImagePullStart()
    # add them to your tree
    self.add_start(start)
    image_not_found = ImageNotFound()
    image_forbidden = ImageForbidden()
    image_dns_issue = ImageDnsIssue()
    image_connection_timeout_restricted_private = ImageConnectionTimeoutRestrictedPrivate(
    )
    image_connection_timeout = ImageConnectionTimeout()
    image_not_found_insufficient_scope = ImageNotFoundInsufficientScope()
    # Describe the step relationships
    self.add_step(parent=start, child=image_not_found)
    self.add_step(parent=image_not_found, child=image_forbidden)
    self.add_step(parent=image_forbidden, child=image_dns_issue)
    self.add_step(parent=image_dns_issue,
                  child=image_connection_timeout_restricted_private)
    self.add_step(parent=image_connection_timeout_restricted_private,
                  child=image_connection_timeout)
    self.add_step(parent=image_connection_timeout,
                  child=image_not_found_insufficient_scope)
    # Ending runbook
    self.add_end(ImagePullEnd())


class ImagePullStart(runbook.StartStep):
  """Initiates diagnostics for Image pull runbook.

  Check
  - if logging API is enabled
  - if there are GKE clusters in the project
  - if a cluster name is provided, verify if that cluster exists in the project
  - if a location is provided, verify there are clusters in that location
  - if both a location and a name are provided, verify that the cluster exists at that location
  """

  def execute(self):
    """Starting the image pull error diagnostics"""

    # skip if logging is disabled
    project = op.get(flags.PROJECT_ID)
    project_path = crm.get_project(project)
    if not apis.is_enabled(project, 'logging'):
      op.add_skipped(project_path,
                     reason=('Logging disabled in project {}').format(project))
      return

    # check if there are clusters in the project
    clusters = gke.get_clusters(op.context)
    if not clusters:
      op.add_skipped(
          project_path,
          reason=('No GKE clusters found in project {}').format(project))
      return

    # following checks are necessary, depending on what input is provided:
    # - no input, get all clusters available
    # - just cluster name is provided, check if there's a cluster with that name
    # - just location is provided, check if there are clusters at that location
    # - cluster name and location are provided, check if there's that cluster at that location
    cluster_name = op.get(flags.NAME)
    cluster_location = op.get(flags.LOCATION)
    found_cluster = False
    found_cluster_with_location = False
    found_clusters_at_location = False
    if cluster_name and cluster_location:
      for cluster in clusters.values():
        if cluster_name == cluster.name \
          and cluster_location == cluster.location:
          found_cluster_with_location = True
          break
    elif cluster_name:
      for cluster in clusters.values():
        if cluster_name == cluster.name:
          found_cluster = True
          break
    elif cluster_location:
      for cluster in clusters.values():
        if cluster_location == cluster.location:
          found_clusters_at_location = True
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


class ImageNotFound(runbook.Step):
  """Check for Image not found log entries"""
  template = 'imagepull::image_not_found'

  def execute(self):
    """
    Check for "Failed to pull image.*not found" log entries
    """
    project = op.get(flags.PROJECT_ID)
    project_path = crm.get_project(project)
    cluster_location = op.get(flags.LOCATION)
    cluster_name = op.get(flags.NAME)
    start_time_utc = op.get(flags.START_TIME_UTC)
    end_time_utc = op.get(flags.END_TIME_UTC)
    filter_list = [
        'log_id("events")',
        'resource.type="k8s_pod"',
        'jsonPayload.message:"Failed to pull image"',
        'jsonPayload.message:"not found"',
    ]

    if cluster_location and cluster_name:
      filter_list.append(f'resource.labels.location="{cluster_location}"')
      filter_list.append(f'resource.labels.cluster_name="{cluster_name}"')

    log_entries = local_realtime_query(filter_list)

    if log_entries:
      sample_log = format_log_entries(log_entries)
      op.add_failed(project_path,
                    reason=op.prep_msg(
                        op.FAILURE_REASON,
                        LOG_ENTRY=sample_log,
                        START_TIME_UTC=start_time_utc,
                        END_TIME_UTC=end_time_utc,
                    ),
                    remediation=op.prep_msg(op.FAILURE_REMEDIATION))
    else:
      op.add_ok(project_path,
                reason=op.prep_msg(op.SUCCESS_REASON,
                                   START_TIME_UTC=start_time_utc,
                                   END_TIME_UTC=end_time_utc))


class ImageForbidden(runbook.Step):
  """Image cannot be pulled, insufficiente permissions"""
  template = 'imagepull::image_forbidden'

  def execute(self):
    """
    Check for "Failed to pull image.*403 Forbidden" log entries
    """
    project = op.get(flags.PROJECT_ID)
    project_path = crm.get_project(project)
    cluster_location = op.get(flags.LOCATION)
    cluster_name = op.get(flags.NAME)
    start_time_utc = op.get(flags.START_TIME_UTC)
    end_time_utc = op.get(flags.END_TIME_UTC)
    filter_list = [
        'log_id("events")',
        'resource.type="k8s_pod"',
        'jsonPayload.message:"Failed to pull image"',
        'jsonPayload.message:"403 Forbidden"',
    ]
    if cluster_location and cluster_name:
      filter_list.append(f'resource.labels.location="{cluster_location}"')
      filter_list.append(f'resource.labels.cluster_name="{cluster_name}"')

    log_entries = local_realtime_query(filter_list)

    if log_entries:
      sample_log = format_log_entries(log_entries)
      op.add_failed(project_path,
                    reason=op.prep_msg(
                        op.FAILURE_REASON,
                        LOG_ENTRY=sample_log,
                        START_TIME_UTC=start_time_utc,
                        END_TIME_UTC=end_time_utc,
                    ),
                    remediation=op.prep_msg(op.FAILURE_REMEDIATION))
    else:
      op.add_ok(project_path,
                reason=op.prep_msg(op.SUCCESS_REASON,
                                   START_TIME_UTC=start_time_utc,
                                   END_TIME_UTC=end_time_utc))


class ImageDnsIssue(runbook.Step):
  """Node DNS sever cannot resolve the IP of the repository"""
  template = 'imagepull::image_dns_issue'

  def execute(self):
    """
    Check for "Failed to pull image.*lookup.*server misbehaving" log entries
    """
    project = op.get(flags.PROJECT_ID)
    project_path = crm.get_project(project)
    cluster_location = op.get(flags.LOCATION)
    cluster_name = op.get(flags.NAME)
    start_time_utc = op.get(flags.START_TIME_UTC)
    end_time_utc = op.get(flags.END_TIME_UTC)
    filter_list = [
        'log_id("events")',
        'resource.type="k8s_pod"',
        'jsonPayload.message:"Failed to pull image"',
        'jsonPayload.message:"lookup"',
        'jsonPayload.message:"server misbehaving"',
    ]
    if cluster_location and cluster_name:
      filter_list.append(f'resource.labels.location="{cluster_location}"')
      filter_list.append(f'resource.labels.cluster_name="{cluster_name}"')

    log_entries = local_realtime_query(filter_list)

    if log_entries:
      sample_log = format_log_entries(log_entries)
      op.add_failed(project_path,
                    reason=op.prep_msg(
                        op.FAILURE_REASON,
                        LOG_ENTRY=sample_log,
                        START_TIME_UTC=start_time_utc,
                        END_TIME_UTC=end_time_utc,
                    ),
                    remediation=op.prep_msg(op.FAILURE_REMEDIATION))
    else:
      op.add_ok(project_path,
                reason=op.prep_msg(op.SUCCESS_REASON,
                                   START_TIME_UTC=start_time_utc,
                                   END_TIME_UTC=end_time_utc))


class ImageConnectionTimeoutRestrictedPrivate(runbook.Step):
  """The connection to restricted.googleapis.com or private.googleapis.com is timing out"""
  template = 'imagepull::image_connection_timeout_restricted_private'

  def execute(self):
    """
    Check for "Failed to pull image.*dial tcp.*199.36.153.\\d:443: i/o timeout" log entries
    """
    project = op.get(flags.PROJECT_ID)
    project_path = crm.get_project(project)
    cluster_location = op.get(flags.LOCATION)
    cluster_name = op.get(flags.NAME)
    start_time_utc = op.get(flags.START_TIME_UTC)
    end_time_utc = op.get(flags.END_TIME_UTC)
    filter_list = [
        'log_id("events")',
        'resource.type="k8s_pod"',
        'jsonPayload.message:"Failed to pull image"',
        'jsonPayload.message:"dial tcp"',
        'jsonPayload.message:"199.36.153.*:443: i/o timeout"',
    ]
    if cluster_location and cluster_name:
      filter_list.append(f'resource.labels.location="{cluster_location}"')
      filter_list.append(f'resource.labels.cluster_name="{cluster_name}"')

    log_entries = local_realtime_query(filter_list)

    if log_entries:
      sample_log = format_log_entries(log_entries)
      op.add_failed(project_path,
                    reason=op.prep_msg(
                        op.FAILURE_REASON,
                        LOG_ENTRY=sample_log,
                        START_TIME_UTC=start_time_utc,
                        END_TIME_UTC=end_time_utc,
                    ),
                    remediation=op.prep_msg(op.FAILURE_REMEDIATION))
    else:
      op.add_ok(project_path,
                reason=op.prep_msg(op.SUCCESS_REASON,
                                   START_TIME_UTC=start_time_utc,
                                   END_TIME_UTC=end_time_utc))


class ImageConnectionTimeout(runbook.Step):
  """The connection to Google APIs is timing out"""
  template = 'imagepull::image_connection_timeout'

  def execute(self):
    """
    Check for "Failed to pull image.*dial tcp.*i/o timeout" log entries
    """
    project = op.get(flags.PROJECT_ID)
    project_path = crm.get_project(project)
    cluster_location = op.get(flags.LOCATION)
    cluster_name = op.get(flags.NAME)
    start_time_utc = op.get(flags.START_TIME_UTC)
    end_time_utc = op.get(flags.END_TIME_UTC)
    filter_list = [
        'log_id("events")',
        'resource.type="k8s_pod"',
        'jsonPayload.message:"Failed to pull image"',
        'jsonPayload.message:"dial tcp"',
        'jsonPayload.message:"i/o timeout"',
    ]
    if cluster_location and cluster_name:
      filter_list.append(f'resource.labels.location="{cluster_location}"')
      filter_list.append(f'resource.labels.cluster_name="{cluster_name}"')

    log_entries = local_realtime_query(filter_list)

    if log_entries:
      sample_log = format_log_entries(log_entries)
      op.add_failed(project_path,
                    reason=op.prep_msg(
                        op.FAILURE_REASON,
                        LOG_ENTRY=sample_log,
                        START_TIME_UTC=start_time_utc,
                        END_TIME_UTC=end_time_utc,
                    ),
                    remediation=op.prep_msg(op.FAILURE_REMEDIATION))
    else:
      op.add_ok(project_path,
                reason=op.prep_msg(op.SUCCESS_REASON,
                                   START_TIME_UTC=start_time_utc,
                                   END_TIME_UTC=end_time_utc))


class ImageNotFoundInsufficientScope(runbook.Step):
  """Check for Image not found log entries with insufficient_scope server message"""
  template = 'imagepull::image_not_found_insufficient_scope'

  def execute(self):
    """
    Check for "Failed to pull image.*insufficient_scope" log entries
    """
    project = op.get(flags.PROJECT_ID)
    project_path = crm.get_project(project)
    cluster_location = op.get(flags.LOCATION)
    cluster_name = op.get(flags.NAME)
    start_time_utc = op.get(flags.START_TIME_UTC)
    end_time_utc = op.get(flags.END_TIME_UTC)
    filter_list = [
        'log_id("events")',
        'resource.type="k8s_pod"',
        'jsonPayload.message:"Failed to pull image"',
        'jsonPayload.message:"insufficient_scope"',
    ]

    if cluster_location and cluster_name:
      filter_list.append(f'resource.labels.location="{cluster_location}"')
      filter_list.append(f'resource.labels.cluster_name="{cluster_name}"')

    log_entries = local_realtime_query(filter_list)
    if log_entries:
      sample_log = format_log_entries(log_entries)
      op.add_failed(project_path,
                    reason=op.prep_msg(
                        op.FAILURE_REASON,
                        LOG_ENTRY=sample_log,
                        START_TIME_UTC=start_time_utc,
                        END_TIME_UTC=end_time_utc,
                    ),
                    remediation=op.prep_msg(op.FAILURE_REMEDIATION))
    else:
      op.add_ok(project_path,
                reason=op.prep_msg(op.SUCCESS_REASON,
                                   START_TIME_UTC=start_time_utc,
                                   END_TIME_UTC=end_time_utc))


class ImagePullEnd(runbook.EndStep):
  """Finalizes the diagnostics process for `GKE Image Pull runbbok`.

  This step prompts the user to confirm satisfaction with the analysis performed for
  `GKE Image Pull runbbok`.

  Depending on the user's response, it may conclude the runbook execution or trigger additional
  steps, such as generating a report of the findings.
  """

  def execute(self):
    """Finalizing `GKE Image Pull runbbok` diagnostics..."""
    response = op.prompt(
        kind=op.CONFIRMATION,
        message='Are you satisfied with the `GKE Image Pull runbbok` analysis?')
    if response == op.NO:
      op.info(message=op.END_MESSAGE)


def format_log_entries(log_entries):
  """Formats a list of log entries into a readable string.

  Args:
    log_entries: A list of log entry dictionaries.

  Returns:
    A formatted string containing information from all log entries.
  """

  log_entry = log_entries[-1]
  formatted_log = []

  labels = get_path(log_entry, ('resource', 'labels'),
                    default={})  # Provide default empty dict
  if labels:
    formatted_log.extend([
        f"Cluster name: {labels.get('cluster_name', 'N/A')}",
        f"Location: {labels.get('location', 'N/A')}",
        f"Namespace Name: {labels.get('namespace_name', 'N/A')}",
        f"Pod Name: {labels.get('pod_name', 'N/A')}",
        f"Project ID: {labels.get('project_id', 'N/A')}"
    ])
  else:
    formatted_log.extend([
        'Cluster name: Not found', 'Location: Not found',
        'Namespace Name: Not found', 'Pod Name: Not found',
        'Project ID: Not found'
    ])

  json_payload = get_path(log_entry, ('jsonPayload',),
                          default={})  # Provide default empty dict
  formatted_log.extend([
      f"Log Message: {json_payload.get('message', 'N/A')}",
      f"Reporting Instance: {json_payload.get('reportingInstance', 'N/A')}",
      f"Last Timestamp: {json_payload.get('lastTimestamp', 'N/A')}"
  ])

  return '\n'.join(formatted_log)
