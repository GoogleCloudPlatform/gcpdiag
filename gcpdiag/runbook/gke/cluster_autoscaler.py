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
"""GKE Cluster Autoscaler runbook"""

from gcpdiag import runbook
from gcpdiag.executor import get_executor
from gcpdiag.queries import apis, crm, gke, logs
from gcpdiag.runbook import op
from gcpdiag.runbook.gke import flags


def local_log_search(project, cluster_name, cluster_location, error_message):
  filter_str = ''
  if cluster_name and cluster_location:
    filter_str += f'resource.labels.location="{cluster_location}" AND \
      resource.labels.cluster_name="{cluster_name}" AND {error_message}'

  elif cluster_name:
    filter_str += f'resource.labels.cluster_name="{cluster_name}" AND {error_message}'
  elif cluster_location:
    filter_str += f'resource.labels.location="{cluster_location}" AND {error_message}'
  else:
    filter_str += f'{error_message}'

  log_entries = logs.query(
      project_id=project,
      resource_type='k8s_cluster',
      log_name=
      'log_id("container.googleapis.com/cluster-autoscaler-visibility")',
      filter_str=filter_str)

  executor = get_executor()
  logs.execute_queries(executor)
  return log_entries


class ClusterAutoscaler(runbook.DiagnosticTree):
  """Analyses logs in the project where the cluster is running.

  If there are log entries that contain messages listed in the public documentation
  https://cloud.google.com/kubernetes-engine/docs/how-to/cluster-autoscaler-visibility#messages
  then provide details on how each particular issue can be solved.

  The following ScaleUP logs messages are covered:
  - scale.up.error.out.of.resources
  - scale.up.error.quota.exceeded
  - scale.up.error.waiting.for.instances.timeout
  - scale.up.error.ip.space.exhausted
  - scale.up.error.service.account.deleted

  The following ScaleDown logs messages are covered:
  - scale.down.error.failed.to.evict.pods
  - no.scale.down.node.node.group.min.size.reached
  """
  # Specify parameters common to all steps in the diagnostic tree class.
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
              False
      },
      flags.LOCATION: {
          'type': str,
          'help': 'The zone or region of the GKE cluster',
          'required': False
      }
  }

  def build_tree(self):
    start = ClusterAutoscalerStart()
    out_of_resources = CaOutOfResources()
    quota_exceeded = CaQuotaExceeded()
    instance_timeout = CaInstanceTimeout()
    ip_space_exhausted = CaIpSpaceExhausted()
    service_account_deleted = CaServiceAccountDeleted()
    min_size_reached = CaMinSizeReached()
    failed_to_evict_pods = CaFailedToEvictPods()
    end = ClusterAutoscalerEnd()

    self.add_start(step=start)
    self.add_step(parent=start, child=out_of_resources)
    self.add_step(parent=out_of_resources, child=quota_exceeded)
    self.add_step(parent=quota_exceeded, child=instance_timeout)
    self.add_step(parent=instance_timeout, child=ip_space_exhausted)
    self.add_step(parent=ip_space_exhausted, child=service_account_deleted)
    self.add_step(parent=service_account_deleted, child=min_size_reached)
    self.add_step(parent=min_size_reached, child=failed_to_evict_pods)
    self.add_end(step=end)


class ClusterAutoscalerStart(runbook.StartStep):
  """Initiates diagnostics for Cluster Autoscaler.

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
        if cluster_name == str(cluster).rsplit('/', maxsplit=1)[-1] \
          and cluster_location == str(cluster).split('/')[-3]:
          found_cluster_with_location = True
          break
    elif cluster_name:
      for cluster in clusters.values():
        if cluster_name == str(cluster).rsplit('/', maxsplit=1)[-1]:
          found_cluster = True
          break
    elif cluster_location:
      for cluster in clusters.values():
        if cluster_location == str(cluster).split('/')[-3]:
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


class CaOutOfResources(runbook.Step):
  """Check for "scale.up.error.out.of.resources" log entries"""
  template = 'clusterautoscaler::out_of_resources'

  def execute(self):
    """
    Check for "scale.up.error.out.of.resources" log entries
    """
    project = op.get(flags.PROJECT_ID)
    project_path = crm.get_project(project)
    cluster_location = op.get(flags.LOCATION)
    cluster_name = op.get(flags.NAME)
    error_message = 'jsonPayload.resultInfo.results.errorMsg.messageId=\
      "scale.up.error.out.of.resources"'

    log_entries = local_log_search(project, cluster_name, cluster_location,
                                   error_message)

    if log_entries.entries:
      for log_entry in log_entries.entries:
        sample_log = log_entry
        break
      op.add_failed(project_path,
                    reason=op.prep_msg(op.FAILURE_REASON, LOG_ENTRY=sample_log),
                    remediation=op.prep_msg(op.FAILURE_REMEDIATION))
    else:
      op.add_ok(project_path,
                reason=op.prep_msg(op.SUCCESS_REASON,
                                   START_TIME_UTC=op.get(flags.START_TIME_UTC),
                                   END_TIME_UTC=op.get(flags.END_TIME_UTC)))


class CaQuotaExceeded(runbook.Step):
  """Check for "scale.up.error.quota.exceeded" log entries"""

  template = 'clusterautoscaler::quota_exceeded'

  def execute(self):
    """
    Check for "scale.up.error.quota.exceeded" log entries
    """
    project = op.get(flags.PROJECT_ID)
    project_path = crm.get_project(project)
    cluster_location = op.get(flags.LOCATION)
    cluster_name = op.get(flags.NAME)
    error_message = 'jsonPayload.resultInfo.results.errorMsg.messageId=\
      "scale.up.error.quota.exceeded"'

    log_entries = local_log_search(project, cluster_name, cluster_location,
                                   error_message)

    if log_entries.entries:
      for log_entry in log_entries.entries:
        sample_log = log_entry
        break
      op.add_failed(project_path,
                    reason=op.prep_msg(op.FAILURE_REASON, LOG_ENTRY=sample_log),
                    remediation=op.prep_msg(op.FAILURE_REMEDIATION))
    else:
      op.add_ok(project_path,
                reason=op.prep_msg(op.SUCCESS_REASON,
                                   START_TIME_UTC=op.get(flags.START_TIME_UTC),
                                   END_TIME_UTC=op.get(flags.END_TIME_UTC)))


class CaInstanceTimeout(runbook.Step):
  """Check for "scale.up.error.waiting.for.instances.timeout" log entries"""

  template = 'clusterautoscaler::instance_timeout'

  def execute(self):
    """
    Check for "scale.up.error.waiting.for.instances.timeout" log entries
    """
    project = op.get(flags.PROJECT_ID)
    project_path = crm.get_project(project)
    cluster_location = op.get(flags.LOCATION)
    cluster_name = op.get(flags.NAME)
    error_message = 'jsonPayload.resultInfo.results.errorMsg.messageId=\
      "scale.up.error.waiting.for.instances.timeout"'

    log_entries = local_log_search(project, cluster_name, cluster_location,
                                   error_message)

    if log_entries.entries:
      for log_entry in log_entries.entries:
        sample_log = log_entry
        break
      op.add_failed(project_path,
                    reason=op.prep_msg(op.FAILURE_REASON, LOG_ENTRY=sample_log),
                    remediation=op.prep_msg(op.FAILURE_REMEDIATION))
    else:
      op.add_ok(project_path,
                reason=op.prep_msg(op.SUCCESS_REASON,
                                   START_TIME_UTC=op.get(flags.START_TIME_UTC),
                                   END_TIME_UTC=op.get(flags.END_TIME_UTC)))


class CaIpSpaceExhausted(runbook.Step):
  """Check for "scale.up.error.ip.space.exhausted" log entries"""

  template = 'clusterautoscaler::ip_space_exhausted'

  def execute(self):
    """
    Check for "scale.up.error.ip.space.exhausted" log entries
    """
    project = op.get(flags.PROJECT_ID)
    project_path = crm.get_project(project)
    cluster_location = op.get(flags.LOCATION)
    cluster_name = op.get(flags.NAME)
    error_message = 'jsonPayload.resultInfo.results.errorMsg.messageId=\
      "scale.up.error.ip.space.exhausted"'

    log_entries = local_log_search(project, cluster_name, cluster_location,
                                   error_message)

    if log_entries.entries:
      for log_entry in log_entries.entries:
        sample_log = log_entry
        break
      op.add_failed(project_path,
                    reason=op.prep_msg(op.FAILURE_REASON, LOG_ENTRY=sample_log),
                    remediation=op.prep_msg(op.FAILURE_REMEDIATION))
    else:
      op.add_ok(project_path,
                reason=op.prep_msg(op.SUCCESS_REASON,
                                   START_TIME_UTC=op.get(flags.START_TIME_UTC),
                                   END_TIME_UTC=op.get(flags.END_TIME_UTC)))


class CaServiceAccountDeleted(runbook.Step):
  """Check for "scale.up.error.service.account.deleted" log entries"""

  template = 'clusterautoscaler::service_account_deleted'

  def execute(self):
    """
    Check for "scale.up.error.service.account.deleted" log entries
    """
    project = op.get(flags.PROJECT_ID)
    project_path = crm.get_project(project)
    cluster_location = op.get(flags.LOCATION)
    cluster_name = op.get(flags.NAME)
    error_message = 'jsonPayload.resultInfo.results.errorMsg.messageId=\
      "scale.up.error.service.account.deleted"'

    log_entries = local_log_search(project, cluster_name, cluster_location,
                                   error_message)

    if log_entries.entries:
      for log_entry in log_entries.entries:
        sample_log = log_entry
        break
      op.add_failed(project_path,
                    reason=op.prep_msg(op.FAILURE_REASON, LOG_ENTRY=sample_log),
                    remediation=op.prep_msg(op.FAILURE_REMEDIATION))
    else:
      op.add_ok(project_path,
                reason=op.prep_msg(op.SUCCESS_REASON,
                                   START_TIME_UTC=op.get(flags.START_TIME_UTC),
                                   END_TIME_UTC=op.get(flags.END_TIME_UTC)))


class CaMinSizeReached(runbook.Step):
  """Check for "no.scale.down.node.node.group.min.size.reached" log entries"""

  template = 'clusterautoscaler::min_size_reached'

  def execute(self):
    """
    Check for "no.scale.down.node.node.group.min.size.reached" log entries
    """
    project = op.get(flags.PROJECT_ID)
    project_path = crm.get_project(project)
    cluster_location = op.get(flags.LOCATION)
    cluster_name = op.get(flags.NAME)
    error_message = 'jsonPayload.noDecisionStatus.noScaleDown.nodes.reason.messageId=\
      "no.scale.down.node.node.group.min.size.reached"'

    log_entries = local_log_search(project, cluster_name, cluster_location,
                                   error_message)

    if log_entries.entries:
      for log_entry in log_entries.entries:
        sample_log = log_entry
        break
      op.add_failed(project_path,
                    reason=op.prep_msg(op.FAILURE_REASON, LOG_ENTRY=sample_log),
                    remediation=op.prep_msg(op.FAILURE_REMEDIATION))
    else:
      op.add_ok(project_path,
                reason=op.prep_msg(op.SUCCESS_REASON,
                                   START_TIME_UTC=op.get(flags.START_TIME_UTC),
                                   END_TIME_UTC=op.get(flags.END_TIME_UTC)))


class CaFailedToEvictPods(runbook.Step):
  """Check for "scale.down.error.failed.to.evict.pods" log entries"""

  template = 'clusterautoscaler::failed_evict_pods'

  def execute(self):
    """
    Check for "scale.down.error.failed.to.evict.pods" log entries
    """
    project = op.get(flags.PROJECT_ID)
    project_path = crm.get_project(project)
    cluster_location = op.get(flags.LOCATION)
    cluster_name = op.get(flags.NAME)
    error_message = 'jsonPayload.resultInfo.results.errorMsg.messageId=\
      "scale.down.error.failed.to.evict.pods"'

    log_entries = local_log_search(project, cluster_name, cluster_location,
                                   error_message)

    if log_entries.entries:
      for log_entry in log_entries.entries:
        sample_log = log_entry
        break
      op.add_failed(project_path,
                    reason=op.prep_msg(op.FAILURE_REASON, LOG_ENTRY=sample_log),
                    remediation=op.prep_msg(op.FAILURE_REMEDIATION))
    else:
      op.add_ok(project_path,
                reason=op.prep_msg(op.SUCCESS_REASON,
                                   START_TIME_UTC=op.get(flags.START_TIME_UTC),
                                   END_TIME_UTC=op.get(flags.END_TIME_UTC)))


class ClusterAutoscalerEnd(runbook.EndStep):
  """Finalizes the diagnostics process for `Cluster Autoscaler`.

  This step prompts the user to confirm satisfaction with the Root Cause Analysis (RCA)
  performed for `Cluster Autoscaler`.

  Depending on the user's response, it may conclude the runbook execution or trigger additional
  steps, such as generating a report of the findings.
  """

  def execute(self):
    """Finalizing `Cluster Autoscaler` diagnostics..."""
    response = op.prompt(
        step=op.CONFIRMATION,
        message=
        'Are you satisfied with the `GKE Cluster Autoscaler` RCA performed?')
    if response == op.NO:
      op.info(message=op.END_MESSAGE)
      op.interface.rm.generate_report()
