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
"""GKE Node Auto Repair runbook"""

from gcpdiag import models, runbook
from gcpdiag.queries import crm, gke, logs
from gcpdiag.runbook import op
from gcpdiag.runbook.gke import flags


def local_realtime_query(filter_str):
  result = logs.realtime_query(project_id=op.get(flags.PROJECT_ID),
                               start_time_utc=op.get(flags.START_TIME_UTC),
                               end_time_utc=op.get(flags.END_TIME_UTC),
                               filter_str=filter_str)
  return result


def unallocatable_gpu_tpu(node, location=None, name=None, gpu=False, tpu=False):
  # the logs for repairs caused by unallocatable TPU or GPU are very similar, so it's worth having
  # one function for both. If a node has unallocatable TPU or GPU
  # - it will be marked as NodeNotSchedulable
  # and there will be log entries with"
  # - '"Updated allocatable" device="google.com/tpu"' for unallocatable TPU
  # - '"Updated allocatable" device="nvidia.com/gpu"' for unallocatable GPU
  # we check the logs for the presence of both events and if both are present, then unallocatable
  # TPU/GPU is the reason for auto-repair.
  filter_str = [
      'log_id("events")', f'resource.labels.node_name="{node}"',
      'jsonPayload.reason="NodeNotSchedulable"'
  ]
  if location:
    filter_str.append(f'resource.labels.location="{location}"')
  if name:
    filter_str.append(f'resource.labels.cluster_name="{name}"')

  filter_str = '\n'.join(filter_str)

  log_entries_event = local_realtime_query(filter_str)

  filter_str = [
      'log_id("kubelet")', f'resource.labels.node_name="{node}"',
      'jsonPayload.MESSAGE:"Updated allocatable"'
  ]
  if tpu:
    filter_str.append('jsonPayload.MESSAGE:"google.com/tpu"')
  if gpu:
    filter_str.append('jsonPayload.MESSAGE:"nvidia.com/gpu"')
  if location:
    filter_str.append(f'resource.labels.location="{location}"')
  if name:
    filter_str.append(f'resource.labels.cluster_name="{name}"')

  filter_str = '\n'.join(filter_str)

  log_entries_kubelet = local_realtime_query(filter_str)

  return log_entries_event and log_entries_kubelet


def check_node_unhealthy(node,
                         location=None,
                         name=None,
                         unhealthy_status='NodeNotReady'):
  """Checks if a node has been in the specified unhealthy status.

  Args:
    node: The name of the GKE node to check.
    location: The zone of the node. Optional.
    name: The name of the GKE cluster. Optional.
    unhealthy_status: The unhealthy status to check for. Defaults to 'NodeNotReady'.
                      It can be 'NodeNotReady' or 'NodeHasDiskPressure'.

  Returns:
    True if the node has been in the specified unhealthy status, False otherwise.
  """

  filter_str = [
      'log_id("events")',
      f'resource.labels.node_name="{node}"',
      f'jsonPayload.message="Node {node} status is now: {unhealthy_status}"',
  ]
  if location:
    filter_str.append(f'resource.labels.location="{location}"')
  if name:
    filter_str.append(f'resource.labels.cluster_name="{name}"')

  filter_str = '\n'.join(filter_str)

  log_entries = local_realtime_query(filter_str)

  # Check if there are any log entries indicating the node was in the specified unhealthy status
  if log_entries:
    return True

  return False


class NodeAutoRepair(runbook.DiagnosticTree):
  """Provides the reason why a Node was auto-repaired

  This runbook checks if:
  - Node auto-repair is enabled on the cluster
  - Nodes was repaired because it was in NotReady status for more than 10 minutes
  - Nodes was repaired because it had disk pressure
  - Nodes was repaired because of unallocatable GPUs
  - Nodes was repaired because of unallocatable TPUs
  """
  parameters = {
      flags.NAME: {
          'type':
              str,
          'help':
              'The name of the GKE cluster, to limit search only for this cluster',
          'required':
              False
      },
      flags.NODE: {
          'type': str,
          'help': 'The node name with issues.',
          'required': True
      },
      flags.LOCATION: {
          'type': str,
          'help': 'The zone of the GKE node',
          'required': False
      }
  }

  def build_tree(self):
    """Construct the diagnostic tree with appropriate steps."""
    start = NodeAutoRepairStart()
    node_notready_check = NodeNotReady()
    node_disk_full_check = NodeDiskFull()
    unallocatable_gpu_check = UnallocatableGpu()
    unallocatable_tpu_check = UnallocatableTpu()

    self.add_start(start)
    self.add_step(parent=start, child=node_notready_check)
    self.add_step(parent=node_notready_check, child=node_disk_full_check)
    self.add_step(parent=node_disk_full_check, child=unallocatable_gpu_check)
    self.add_step(parent=unallocatable_gpu_check, child=unallocatable_tpu_check)
    self.add_end(step=NodeAutoRepairEnd())


class NodeAutoRepairStart(runbook.StartStep):
  """Check inputs and verify if there actually was a repair event"""

  def execute(self):
    """Check inputs and verify if there was a repair event"""
    project = op.get(flags.PROJECT_ID)
    location = op.get(flags.LOCATION)
    node = op.get(flags.NODE)
    name = op.get(flags.NAME)
    project_path = crm.get_project(project)
    start_time_utc = op.get(flags.START_TIME_UTC)
    end_time_utc = op.get(flags.END_TIME_UTC)

    # check if there are clusters in the project
    if name:
      clusters = gke.get_clusters(
          models.Context(project_id=project, resources=[name]))
      if not clusters:
        op.add_skipped(
            project_path,
            reason=(f'No {name} GKE cluster found in project {project}'))
        return
    else:
      clusters = gke.get_clusters(op.context)
      if not clusters:
        op.add_skipped(project_path,
                       reason=(f'No GKE clusters found in project {project}'))
        return

    # check if there were any repair operations for provided node
    filter_str = [
        'log_id("cloudaudit.googleapis.com/activity")',
        'protoPayload.methodName="io.k8s.core.v1.nodes.update"',
        'protoPayload.request.metadata.annotations."gke-current-operation":"AUTO_REPAIR_NODES"',
        f'protoPayload.resourceName="core/v1/nodes/{node}"'
    ]
    if location:
      filter_str.append(f'resource.labels.location="{location}"')
    if name:
      filter_str.append(f'resource.labels.cluster_name="{name}"')

    filter_str = '\n'.join(filter_str)

    log_entries = local_realtime_query(filter_str)

    if not log_entries:
      reason = f'There are no node repair operations for node {node}'
      if name:
        reason += f' in cluster {name}'
      if location:
        reason += f' in location {location}'
      reason += f' in the provided time range {start_time_utc} - {end_time_utc}.'
      op.add_skipped(project_path, reason=reason)
      return


class NodeNotReady(runbook.Step):
  """Checks if nodes have been in NotReady status for an extended period (e.g., 10 minutes)."""

  template = 'nodeautorepair::node_notready'

  def execute(self):
    """Checking if there is the node is in NotReady status."""
    project = op.get(flags.PROJECT_ID)
    location = op.get(flags.LOCATION)
    node = op.get(flags.NODE)
    name = op.get(flags.NAME)
    project_path = crm.get_project(project)

    if check_node_unhealthy(node,
                            location,
                            name,
                            unhealthy_status='NodeNotReady'):
      op.add_failed(project_path,
                    reason=op.prep_msg(op.FAILURE_REASON, NODE=node),
                    remediation=op.prep_msg(op.FAILURE_REMEDIATION))
    else:
      op.add_ok(project_path, reason=op.prep_msg(op.SUCCESS_REASON, NODE=node))


class NodeDiskFull(runbook.Step):
  """Checks if node disks are full."""

  template = 'nodeautorepair::node_disk_full'

  def execute(self):
    """Checking if there is the node is in NodeHasDiskPressure status."""
    project = op.get(flags.PROJECT_ID)
    location = op.get(flags.LOCATION)
    node = op.get(flags.NODE)
    name = op.get(flags.NAME)
    project_path = crm.get_project(project)

    if check_node_unhealthy(node,
                            location,
                            name,
                            unhealthy_status='NodeHasDiskPressure'):
      op.add_failed(project_path,
                    reason=op.prep_msg(op.FAILURE_REASON, NODE=node),
                    remediation=op.prep_msg(op.FAILURE_REMEDIATION))
    else:
      op.add_ok(project_path, reason=op.prep_msg(op.SUCCESS_REASON, NODE=node))


class UnallocatableGpu(runbook.Step):
  """Checks GPU allocation"""
  template = 'nodeautorepair::unallocatable_gpu'

  def execute(self):
    """Verify whether the node was auto-repaired because of Unallocatable GPUs."""

    project = op.get(flags.PROJECT_ID)
    location = op.get(flags.LOCATION)
    node = op.get(flags.NODE)
    name = op.get(flags.NAME)
    project_path = crm.get_project(project)

    if unallocatable_gpu_tpu(node, location, name, tpu=False, gpu=True):
      op.add_failed(project_path,
                    reason=op.prep_msg(op.FAILURE_REASON, NODE=node),
                    remediation=op.prep_msg(op.FAILURE_REMEDIATION))
    else:
      op.add_ok(project_path, reason=op.prep_msg(op.SUCCESS_REASON, NODE=node))


class UnallocatableTpu(runbook.Step):
  """Checks TPU allocation"""
  template = 'nodeautorepair::unallocatable_tpu'

  def execute(self):
    """Verify whether the node was auto-repaired because of Unallocatable TPUs."""

    project = op.get(flags.PROJECT_ID)
    location = op.get(flags.LOCATION)
    node = op.get(flags.NODE)
    name = op.get(flags.NAME)
    project_path = crm.get_project(project)

    if unallocatable_gpu_tpu(node, location, name, tpu=True, gpu=False):
      op.add_failed(project_path,
                    reason=op.prep_msg(op.FAILURE_REASON, NODE=node),
                    remediation=op.prep_msg(op.FAILURE_REMEDIATION))
    else:
      op.add_ok(project_path, reason=op.prep_msg(op.SUCCESS_REASON, NODE=node))


class NodeAutoRepairEnd(runbook.EndStep):
  """Finalizes the diagnostics process for `Node AutoRepair`.

  This step prompts the user to confirm satisfaction with the Root Cause Analysis (RCA)
  performed for `Node AutoRepair`.

  Depending on the user's response, it may conclude the runbook execution or trigger additional
  steps, such as generating a report of the findings.
  """

  def execute(self):
    """Finalizing `Node AutoRepair` diagnostics..."""
    response = op.prompt(
        kind=op.CONFIRMATION,
        message='Are you satisfied with the `GKE Node AutoRepair` RCA performed?'
    )
    if response == op.NO:
      op.info(message=op.END_MESSAGE)
      op.operator.interface.rm.generate_report()
