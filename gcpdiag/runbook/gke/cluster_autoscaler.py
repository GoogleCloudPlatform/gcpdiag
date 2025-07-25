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

import json

from gcpdiag import runbook
from gcpdiag.queries import apis, crm, gke, logs
from gcpdiag.runbook import op
from gcpdiag.runbook.gke import flags
from gcpdiag.utils import GcpApiError


def local_log_search(cluster_name, cluster_location, error_message):
  """Constructs a filter string for a logs query function based on provided arguments.

  Args:
    cluster_name: Optional name of the cluster to filter logs for.
    cluster_location: Optional location of the cluster to filter logs for.
    error_message: Required error message to include in the filter.

  Returns:
    A string representing the filter for the logs query.
  """
  filter_list = [
      'log_id("container.googleapis.com/cluster-autoscaler-visibility")',
      'resource.type="k8s_cluster"',
      f'resource.labels.location="{cluster_location}"',
      f'resource.labels.cluster_name="{cluster_name}"', f'{error_message}'
  ]

  filter_str = '\n'.join(filter_list)

  log_entries = logs.realtime_query(project_id=op.get(flags.PROJECT_ID),
                                    start_time=op.get(flags.START_TIME),
                                    end_time=op.get(flags.END_TIME),
                                    filter_str=filter_str)

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
  - no.scale.down.node.scale.down.disabled.annotation
  - no.scale.down.node.minimal.resource.limits.exceeded
  - no.scale.down.node.no.place.to.move.pods
  - no.scale.down.node.pod.not.backed.by.controller
  - no.scale.down.node.pod.not.safe.to.evict.annotation
  - no.scale.down.node.pod.kube.system.unmovable
  - no.scale.down.node.pod.not.enough.pdb
  - no.scale.down.node.pod.controller.not.found
  - no.scale.down.node.pod.unexpected.error

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
              'The name of the GKE cluster, to limit search only for this cluster',
          'deprecated':
              True,
          'new_parameter':
              'gke_cluster_name',
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

  def legacy_parameter_handler(self, parameters):
    if flags.NAME in parameters:
      parameters[flags.GKE_CLUSTER_NAME] = parameters.pop(flags.NAME)

  def build_tree(self):
    start = ClusterAutoscalerStart()
    out_of_resources = CaOutOfResources()
    quota_exceeded = CaQuotaExceeded()
    instance_timeout = CaInstanceTimeout()
    ip_space_exhausted = CaIpSpaceExhausted()
    service_account_deleted = CaServiceAccountDeleted()
    min_size_reached = CaMinSizeReached()
    failed_to_evict_pods = CaFailedToEvictPods()
    disabled_annotation = CaDisabledAnnotation()
    min_resource_limit_exceeded = CaMinResourceLimitExceeded()
    no_place_to_move_pods = CaNoPlaceToMovePods()
    pod_not_backed_by_controller = CaPodsNotBackedByController()
    not_safe_to_evict_annotation = CaNotSafeToEvictAnnotation()
    pod_kube_system_unmovable = CaPodKubeSystemUnmovable()
    pod_not_enough_pdb = CaPodNotEnoughPdb()
    pod_controller_not_found = CaPodControllerNotFound()
    pod_unexpected_error = CaPodUnexpectedError()
    end = ClusterAutoscalerEnd()

    self.add_start(step=start)
    self.add_step(parent=start, child=out_of_resources)
    self.add_step(parent=out_of_resources, child=quota_exceeded)
    self.add_step(parent=quota_exceeded, child=instance_timeout)
    self.add_step(parent=instance_timeout, child=ip_space_exhausted)
    self.add_step(parent=ip_space_exhausted, child=service_account_deleted)
    self.add_step(parent=service_account_deleted, child=min_size_reached)
    self.add_step(parent=min_size_reached, child=failed_to_evict_pods)
    self.add_step(parent=failed_to_evict_pods, child=disabled_annotation)
    self.add_step(parent=disabled_annotation, child=min_resource_limit_exceeded)
    self.add_step(parent=min_resource_limit_exceeded,
                  child=no_place_to_move_pods)
    self.add_step(parent=no_place_to_move_pods,
                  child=pod_not_backed_by_controller)
    self.add_step(parent=pod_not_backed_by_controller,
                  child=not_safe_to_evict_annotation)
    self.add_step(parent=not_safe_to_evict_annotation,
                  child=pod_kube_system_unmovable)
    self.add_step(parent=pod_kube_system_unmovable, child=pod_not_enough_pdb)
    self.add_step(parent=pod_not_enough_pdb, child=pod_controller_not_found)
    self.add_step(parent=pod_controller_not_found, child=pod_unexpected_error)
    self.add_end(step=end)


class ClusterAutoscalerStart(runbook.StartStep):
  """Initiates diagnostics for Cluster Autoscaler.

  Check
  - if logging API is enabled
  - verify that the cluster exists at that location
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

    # verify if the provided cluster at location is present
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
    cluster_name = op.get(flags.GKE_CLUSTER_NAME)
    error_message = ('jsonPayload.resultInfo.results.errorMsg.messageId='
                     '"scale.up.error.out.of.resources"')

    log_entries = local_log_search(cluster_name, cluster_location,
                                   error_message)

    if log_entries:
      for log_entry in log_entries:
        sample_log = json.dumps(log_entry, indent=2)
        break
      op.add_failed(project_path,
                    reason=op.prep_msg(op.FAILURE_REASON, log_entry=sample_log),
                    remediation=op.prep_msg(op.FAILURE_REMEDIATION))
    else:
      op.add_ok(project_path,
                reason=op.prep_msg(op.SUCCESS_REASON,
                                   start_time=op.get(flags.START_TIME),
                                   end_time=op.get(flags.END_TIME)))


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
    cluster_name = op.get(flags.GKE_CLUSTER_NAME)
    error_message = ('jsonPayload.resultInfo.results.errorMsg.messageId='
                     '"scale.up.error.quota.exceeded"')

    log_entries = local_log_search(cluster_name, cluster_location,
                                   error_message)

    if log_entries:
      for log_entry in log_entries:
        sample_log = json.dumps(log_entry, indent=2)
        break
      op.add_failed(project_path,
                    reason=op.prep_msg(op.FAILURE_REASON, log_entry=sample_log),
                    remediation=op.prep_msg(op.FAILURE_REMEDIATION))
    else:
      op.add_ok(project_path,
                reason=op.prep_msg(op.SUCCESS_REASON,
                                   start_time=op.get(flags.START_TIME),
                                   end_time=op.get(flags.END_TIME)))


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
    cluster_name = op.get(flags.GKE_CLUSTER_NAME)
    error_message = ('jsonPayload.resultInfo.results.errorMsg.messageId='
                     '"scale.up.error.waiting.for.instances.timeout"')

    log_entries = local_log_search(cluster_name, cluster_location,
                                   error_message)

    if log_entries:
      for log_entry in log_entries:
        sample_log = json.dumps(log_entry, indent=2)
        break
      op.add_failed(project_path,
                    reason=op.prep_msg(op.FAILURE_REASON, log_entry=sample_log),
                    remediation=op.prep_msg(op.FAILURE_REMEDIATION))
    else:
      op.add_ok(project_path,
                reason=op.prep_msg(op.SUCCESS_REASON,
                                   start_time=op.get(flags.START_TIME),
                                   end_time=op.get(flags.END_TIME)))


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
    cluster_name = op.get(flags.GKE_CLUSTER_NAME)
    error_message = ('jsonPayload.resultInfo.results.errorMsg.messageId='
                     '"scale.up.error.ip.space.exhausted"')

    log_entries = local_log_search(cluster_name, cluster_location,
                                   error_message)

    if log_entries:
      for log_entry in log_entries:
        sample_log = json.dumps(log_entry, indent=2)
        break
      op.add_failed(project_path,
                    reason=op.prep_msg(op.FAILURE_REASON, log_entry=sample_log),
                    remediation=op.prep_msg(op.FAILURE_REMEDIATION))
    else:
      op.add_ok(project_path,
                reason=op.prep_msg(op.SUCCESS_REASON,
                                   start_time=op.get(flags.START_TIME),
                                   end_time=op.get(flags.END_TIME)))


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
    cluster_name = op.get(flags.GKE_CLUSTER_NAME)
    error_message = ('jsonPayload.resultInfo.results.errorMsg.messageId='
                     '"scale.up.error.service.account.deleted"')

    log_entries = local_log_search(cluster_name, cluster_location,
                                   error_message)

    if log_entries:
      for log_entry in log_entries:
        sample_log = json.dumps(log_entry, indent=2)
        break
      op.add_failed(project_path,
                    reason=op.prep_msg(op.FAILURE_REASON, log_entry=sample_log),
                    remediation=op.prep_msg(op.FAILURE_REMEDIATION))
    else:
      op.add_ok(project_path,
                reason=op.prep_msg(op.SUCCESS_REASON,
                                   start_time=op.get(flags.START_TIME),
                                   end_time=op.get(flags.END_TIME)))


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
    cluster_name = op.get(flags.GKE_CLUSTER_NAME)
    error_message = (
        'jsonPayload.noDecisionStatus.noScaleDown.nodes.reason.messageId='
        '"no.scale.down.node.node.group.min.size.reached"')
    log_entries = local_log_search(cluster_name, cluster_location,
                                   error_message)

    if log_entries:
      for log_entry in log_entries:
        sample_log = json.dumps(log_entry, indent=2)
        break
      op.add_failed(project_path,
                    reason=op.prep_msg(op.FAILURE_REASON, log_entry=sample_log),
                    remediation=op.prep_msg(op.FAILURE_REMEDIATION))
    else:
      op.add_ok(project_path,
                reason=op.prep_msg(op.SUCCESS_REASON,
                                   start_time=op.get(flags.START_TIME),
                                   end_time=op.get(flags.END_TIME)))


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
    cluster_name = op.get(flags.GKE_CLUSTER_NAME)
    error_message = ('jsonPayload.resultInfo.results.errorMsg.messageId='
                     '"scale.down.error.failed.to.evict.pods"')

    log_entries = local_log_search(cluster_name, cluster_location,
                                   error_message)

    if log_entries:
      for log_entry in log_entries:
        sample_log = json.dumps(log_entry, indent=2)
        break
      op.add_failed(project_path,
                    reason=op.prep_msg(op.FAILURE_REASON, log_entry=sample_log),
                    remediation=op.prep_msg(op.FAILURE_REMEDIATION))
    else:
      op.add_ok(project_path,
                reason=op.prep_msg(op.SUCCESS_REASON,
                                   start_time=op.get(flags.START_TIME),
                                   end_time=op.get(flags.END_TIME)))


class CaDisabledAnnotation(runbook.Step):
  """Check for "no.scale.down.node.scale.down.disabled.annotation" log entries"""

  template = 'clusterautoscaler::disabled_annotation'

  def execute(self):
    """
    Check for "no.scale.down.node.scale.down.disabled.annotation" log entries
    """
    project = op.get(flags.PROJECT_ID)
    project_path = crm.get_project(project)
    cluster_location = op.get(flags.LOCATION)
    cluster_name = op.get(flags.GKE_CLUSTER_NAME)
    error_message = (
        'jsonPayload.noDecisionStatus.noScaleDown.nodes.reason.messageId='
        '"no.scale.down.node.scale.down.disabled.annotation"')

    log_entries = local_log_search(cluster_name, cluster_location,
                                   error_message)

    if log_entries:
      for log_entry in log_entries:
        sample_log = json.dumps(log_entry, indent=2)
        break
      op.add_failed(project_path,
                    reason=op.prep_msg(op.FAILURE_REASON, log_entry=sample_log),
                    remediation=op.prep_msg(op.FAILURE_REMEDIATION))
    else:
      op.add_ok(project_path,
                reason=op.prep_msg(op.SUCCESS_REASON,
                                   start_time=op.get(flags.START_TIME),
                                   end_time=op.get(flags.END_TIME)))


class CaMinResourceLimitExceeded(runbook.Step):
  """Check for "no.scale.down.node.minimal.resource.limits.exceeded" log entries"""

  template = 'clusterautoscaler::min_resource_limit_exceeded'

  def execute(self):
    """
    Check for "no.scale.down.node.minimal.resource.limits.exceeded" log entries
    """
    project = op.get(flags.PROJECT_ID)
    project_path = crm.get_project(project)
    cluster_location = op.get(flags.LOCATION)
    cluster_name = op.get(flags.GKE_CLUSTER_NAME)
    error_message = (
        'jsonPayload.noDecisionStatus.noScaleDown.nodes.reason.messageId='
        '"no.scale.down.node.minimal.resource.limits.exceeded"')

    log_entries = local_log_search(cluster_name, cluster_location,
                                   error_message)

    if log_entries:
      for log_entry in log_entries:
        sample_log = json.dumps(log_entry, indent=2)
        break
      op.add_failed(project_path,
                    reason=op.prep_msg(op.FAILURE_REASON, log_entry=sample_log),
                    remediation=op.prep_msg(op.FAILURE_REMEDIATION))
    else:
      op.add_ok(project_path,
                reason=op.prep_msg(op.SUCCESS_REASON,
                                   start_time=op.get(flags.START_TIME),
                                   end_time=op.get(flags.END_TIME)))


class CaNoPlaceToMovePods(runbook.Step):
  """Check for "no.scale.down.node.no.place.to.move.pods" log entries"""

  template = 'clusterautoscaler::no_place_to_move_pods'

  def execute(self):
    """
    Check for "no.scale.down.node.no.place.to.move.pods" log entries
    """
    project = op.get(flags.PROJECT_ID)
    project_path = crm.get_project(project)
    cluster_location = op.get(flags.LOCATION)
    cluster_name = op.get(flags.GKE_CLUSTER_NAME)
    error_message = (
        'jsonPayload.noDecisionStatus.noScaleDown.nodes.reason.messageId='
        '"no.scale.down.node.no.place.to.move.pods"')

    log_entries = local_log_search(cluster_name, cluster_location,
                                   error_message)

    if log_entries:
      for log_entry in log_entries:
        sample_log = json.dumps(log_entry, indent=2)
        break
      op.add_failed(project_path,
                    reason=op.prep_msg(op.FAILURE_REASON, log_entry=sample_log),
                    remediation=op.prep_msg(op.FAILURE_REMEDIATION))
    else:
      op.add_ok(project_path,
                reason=op.prep_msg(op.SUCCESS_REASON,
                                   start_time=op.get(flags.START_TIME),
                                   end_time=op.get(flags.END_TIME)))


class CaPodsNotBackedByController(runbook.Step):
  """Check for "no.scale.down.node.pod.not.backed.by.controller" log entries"""

  template = 'clusterautoscaler::pod_not_backed_by_controller'

  def execute(self):
    """
    Check for "no.scale.down.node.pod.not.backed.by.controller" log entries
    """
    project = op.get(flags.PROJECT_ID)
    project_path = crm.get_project(project)
    cluster_location = op.get(flags.LOCATION)
    cluster_name = op.get(flags.GKE_CLUSTER_NAME)
    error_message = (
        'jsonPayload.noDecisionStatus.noScaleDown.nodes.reason.messageId='
        '"no.scale.down.node.pod.not.backed.by.controller"')

    log_entries = local_log_search(cluster_name, cluster_location,
                                   error_message)

    if log_entries:
      for log_entry in log_entries:
        sample_log = json.dumps(log_entry, indent=2)
        break
      op.add_failed(project_path,
                    reason=op.prep_msg(op.FAILURE_REASON, log_entry=sample_log),
                    remediation=op.prep_msg(op.FAILURE_REMEDIATION))
    else:
      op.add_ok(project_path,
                reason=op.prep_msg(op.SUCCESS_REASON,
                                   start_time=op.get(flags.START_TIME),
                                   end_time=op.get(flags.END_TIME)))


class CaNotSafeToEvictAnnotation(runbook.Step):
  """Check for "no.scale.down.node.pod.not.safe.to.evict.annotation" log entries"""

  template = 'clusterautoscaler::not_safe_to_evict_annotation'

  def execute(self):
    """
    Check for "no.scale.down.node.pod.not.safe.to.evict.annotation" log entries
    """
    project = op.get(flags.PROJECT_ID)
    project_path = crm.get_project(project)
    cluster_location = op.get(flags.LOCATION)
    cluster_name = op.get(flags.GKE_CLUSTER_NAME)
    error_message = (
        'jsonPayload.noDecisionStatus.noScaleDown.nodes.reason.messageId='
        '"no.scale.down.node.pod.not.safe.to.evict.annotation"')

    log_entries = local_log_search(cluster_name, cluster_location,
                                   error_message)

    if log_entries:
      for log_entry in log_entries:
        sample_log = json.dumps(log_entry, indent=2)
        break
      op.add_failed(project_path,
                    reason=op.prep_msg(op.FAILURE_REASON, log_entry=sample_log),
                    remediation=op.prep_msg(op.FAILURE_REMEDIATION))
    else:
      op.add_ok(project_path,
                reason=op.prep_msg(op.SUCCESS_REASON,
                                   start_time=op.get(flags.START_TIME),
                                   end_time=op.get(flags.END_TIME)))


class CaPodKubeSystemUnmovable(runbook.Step):
  """Check for "no.scale.down.node.pod.kube.system.unmovable" log entries"""

  template = 'clusterautoscaler::pod_kube_system_unmovable'

  def execute(self):
    """
    Check for "no.scale.down.node.pod.kube.system.unmovable" log entries
    """
    project = op.get(flags.PROJECT_ID)
    project_path = crm.get_project(project)
    cluster_location = op.get(flags.LOCATION)
    cluster_name = op.get(flags.GKE_CLUSTER_NAME)
    error_message = (
        'jsonPayload.noDecisionStatus.noScaleDown.nodes.reason.messageId='
        '"no.scale.down.node.pod.kube.system.unmovable"')

    log_entries = local_log_search(cluster_name, cluster_location,
                                   error_message)

    if log_entries:
      for log_entry in log_entries:
        sample_log = json.dumps(log_entry, indent=2)
        break
      op.add_failed(project_path,
                    reason=op.prep_msg(op.FAILURE_REASON, log_entry=sample_log),
                    remediation=op.prep_msg(op.FAILURE_REMEDIATION))
    else:
      op.add_ok(project_path,
                reason=op.prep_msg(op.SUCCESS_REASON,
                                   start_time=op.get(flags.START_TIME),
                                   end_time=op.get(flags.END_TIME)))


class CaPodNotEnoughPdb(runbook.Step):
  """Check for "no.scale.down.node.pod.not.enough.pdb" log entries"""

  template = 'clusterautoscaler::pod_not_enough_pdb'

  def execute(self):
    """
    Check for "no.scale.down.node.pod.not.enough.pdb" log entries
    """
    project = op.get(flags.PROJECT_ID)
    project_path = crm.get_project(project)
    cluster_location = op.get(flags.LOCATION)
    cluster_name = op.get(flags.GKE_CLUSTER_NAME)
    error_message = (
        'jsonPayload.noDecisionStatus.noScaleDown.nodes.reason.messageId='
        '"no.scale.down.node.pod.not.enough.pdb"')

    log_entries = local_log_search(cluster_name, cluster_location,
                                   error_message)

    if log_entries:
      for log_entry in log_entries:
        sample_log = json.dumps(log_entry, indent=2)
        break
      op.add_failed(project_path,
                    reason=op.prep_msg(op.FAILURE_REASON, log_entry=sample_log),
                    remediation=op.prep_msg(op.FAILURE_REMEDIATION))
    else:
      op.add_ok(project_path,
                reason=op.prep_msg(op.SUCCESS_REASON,
                                   start_time=op.get(flags.START_TIME),
                                   end_time=op.get(flags.END_TIME)))


class CaPodControllerNotFound(runbook.Step):
  """Check for "no.scale.down.node.pod.controller.not.found" log entries"""

  template = 'clusterautoscaler::pod_controller_not_found'

  def execute(self):
    """
    Check for "no.scale.down.node.pod.controller.not.found" log entries
    """
    project = op.get(flags.PROJECT_ID)
    project_path = crm.get_project(project)
    cluster_location = op.get(flags.LOCATION)
    cluster_name = op.get(flags.GKE_CLUSTER_NAME)
    error_message = (
        'jsonPayload.noDecisionStatus.noScaleDown.nodes.reason.messageId='
        '"no.scale.down.node.pod.controller.not.found"')

    log_entries = local_log_search(cluster_name, cluster_location,
                                   error_message)

    if log_entries:
      for log_entry in log_entries:
        sample_log = json.dumps(log_entry, indent=2)
        break
      op.add_failed(project_path,
                    reason=op.prep_msg(op.FAILURE_REASON, log_entry=sample_log),
                    remediation=op.prep_msg(op.FAILURE_REMEDIATION))
    else:
      op.add_ok(project_path,
                reason=op.prep_msg(op.SUCCESS_REASON,
                                   start_time=op.get(flags.START_TIME),
                                   end_time=op.get(flags.END_TIME)))


class CaPodUnexpectedError(runbook.Step):
  """Check for "no.scale.down.node.pod.unexpected.error" log entries"""

  template = 'clusterautoscaler::pod_unexpected_error'

  def execute(self):
    """
    Check for "no.scale.down.node.pod.unexpected.error" log entries
    """
    project = op.get(flags.PROJECT_ID)
    project_path = crm.get_project(project)
    cluster_location = op.get(flags.LOCATION)
    cluster_name = op.get(flags.GKE_CLUSTER_NAME)
    error_message = (
        'jsonPayload.noDecisionStatus.noScaleDown.nodes.reason.messageId='
        '"no.scale.down.node.pod.unexpected.error"')

    log_entries = local_log_search(cluster_name, cluster_location,
                                   error_message)

    if log_entries:
      for log_entry in log_entries:
        sample_log = json.dumps(log_entry, indent=2)
        break
      op.add_failed(project_path,
                    reason=op.prep_msg(op.FAILURE_REASON, log_entry=sample_log),
                    remediation=op.prep_msg(op.FAILURE_REMEDIATION))
    else:
      op.add_ok(project_path,
                reason=op.prep_msg(op.SUCCESS_REASON,
                                   start_time=op.get(flags.START_TIME),
                                   end_time=op.get(flags.END_TIME)))


class ClusterAutoscalerEnd(runbook.EndStep):
  """Finalizes the diagnostics process for `Cluster Autoscaler`.

  This step prompts the user to confirm satisfaction with the Root Cause Analysis (RCA)
  performed for `Cluster Autoscaler`.

  Depending on the user's response, it may conclude the runbook execution or trigger additional
  steps, such as generating a report of the findings.
  """

  def execute(self):
    """Finalize `Cluster Autoscaler` diagnostics."""
    response = op.prompt(
        kind=op.CONFIRMATION,
        message=
        'Are you satisfied with the `GKE Cluster Autoscaler` RCA performed?')
    if response == op.NO:
      op.info(message=op.END_MESSAGE)
