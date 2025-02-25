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
"""GKE Node Unavailability runbook"""

from gcpdiag import runbook
from gcpdiag.queries import crm, gke, logs
from gcpdiag.runbook import op
from gcpdiag.runbook.gke import flags

# local variables to not repeat the same log queries
LOG_PREEMPTED = LOG_DELETED = LOG_MIGRATED = None


def local_realtime_query(filter_str):
  result = logs.realtime_query(project_id=op.get(flags.PROJECT_ID),
                               start_time=op.get(flags.START_TIME),
                               end_time=op.get(flags.END_TIME),
                               filter_str=filter_str)
  return result


class NodeUnavailability(runbook.DiagnosticTree):
  """Identifies the reasons for a GKE node being unavailable.

  This runbook investigates various factors that may have caused a node to become unavailable,
  including:

  - Live Migration
  - Preemption
  - Removal by the Cluster Autoscaler
  - Node Pool Upgrade
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
              'The name of the GKE cluster, to limit search only for this cluster',
          'required':
              False
      },
      flags.NODE: {
          'type': str,
          'help': 'The node name that was started.',
          'required': True
      },
      flags.LOCATION: {
          'type': str,
          'help': 'The zone or region of the GKE cluster',
          'required': False
      }
  }

  def build_tree(self):
    """Construct the diagnostic tree with appropriate steps."""
    start = NodeUnavailabilityStart()
    live_migration_check = LiveMigration()
    preemption_check = PreemptionCondition()
    autoscaler_removal_check = NodeRemovedByAutoscaler()
    upgrade_check = NodePoolUpgrade()

    self.add_start(start)
    self.add_step(parent=start, child=live_migration_check)
    self.add_step(parent=live_migration_check, child=preemption_check)
    self.add_step(parent=preemption_check, child=autoscaler_removal_check)
    self.add_step(parent=autoscaler_removal_check, child=upgrade_check)
    self.add_end(step=NodeUnavailabilityEnd())


class NodeUnavailabilityStart(runbook.StartStep):
  """Check inputs and verify if the node was unavailable"""

  def execute(self):
    """Check inputs and verify if the node was unavailable"""
    project = op.get(flags.PROJECT_ID)
    location = op.get(flags.LOCATION)
    node = op.get(flags.NODE)
    name = op.get(flags.NAME)
    project_path = crm.get_project(project)
    start_time = op.get(flags.START_TIME)
    end_time = op.get(flags.END_TIME)
    global LOG_MIGRATED, LOG_DELETED, LOG_PREEMPTED

    # check if there are clusters in the project
    clusters = gke.get_clusters(op.get_new_context(project_id=project))
    if not clusters:
      op.add_skipped(project_path,
                     reason=f'No GKE clusters found in project {project}')
      return

    # check if there were any node unavailability logs for the provided node

    filter_str = [
        'resource.type="gce_instance"',
        'log_id("cloudaudit.googleapis.com/system_event")',
        'protoPayload.methodName="compute.instances.preempted"',
        f'protoPayload.resourceName:"{node}"'
    ]

    filter_str = '\n'.join(filter_str)
    LOG_PREEMPTED = local_realtime_query(filter_str)

    filter_str = [
        'resource.type="gce_instance"',
        '(protoPayload.methodName="compute.instances.migrateOnHostMaintenance" OR'
        ' operation.producer="compute.instances.migrateOnHostMaintenance")',
        'log_id("cloudaudit.googleapis.com/system_event")',
        f'protoPayload.resourceName:"{node}"'
    ]
    filter_str = '\n'.join(filter_str)
    LOG_MIGRATED = local_realtime_query(filter_str)

    filter_str = [
        'resource.type="gce_instance"',
        'protoPayload.methodName="v1.compute.instances.delete"',
        'log_id("cloudaudit.googleapis.com/activity")',
        f'protoPayload.resourceName:"{node}"'
    ]

    filter_str = '\n'.join(filter_str)
    LOG_DELETED = local_realtime_query(filter_str)

    if not (LOG_PREEMPTED or LOG_MIGRATED or LOG_DELETED):
      reason = f'There are no log entries that would show node {node} being unavailable'
      if name:
        reason += f' in cluster {name}'
      if location:
        reason += f' in location {location}'
      reason += f' in the provided time range {start_time} - {end_time}.'
      op.add_skipped(project_path, reason=reason)
      return


class LiveMigration(runbook.Step):
  """Checks if the node was unavailable due to a live migration event."""

  template = 'nodeunavailability::node_live_migration'

  def execute(self):
    """Check for live migration logs."""
    project = op.get(flags.PROJECT_ID)
    node = op.get(flags.NODE)
    project_path = crm.get_project(project)

    if LOG_MIGRATED:
      op.add_failed(project_path,
                    reason=op.prep_msg(op.FAILURE_REASON, node=node),
                    remediation=op.prep_msg(op.FAILURE_REMEDIATION, node=node))
    else:
      op.add_ok(project_path, reason=op.prep_msg(op.SUCCESS_REASON, node=node))


class PreemptionCondition(runbook.Step):
  """Checks if the node was preempted."""

  template = 'nodeunavailability::node_preempted'

  def execute(self):
    """Checks for preemption logs."""
    project = op.get(flags.PROJECT_ID)
    node = op.get(flags.NODE)
    project_path = crm.get_project(project)

    if LOG_PREEMPTED:
      op.add_failed(project_path,
                    reason=op.prep_msg(op.FAILURE_REASON, node=node),
                    remediation=op.prep_msg(op.FAILURE_REMEDIATION))
    else:
      op.add_ok(project_path, reason=op.prep_msg(op.SUCCESS_REASON, node=node))


class NodeRemovedByAutoscaler(runbook.Step):
  """Checks if the node was removed by Cluster Autoscaler."""

  template = 'nodeunavailability::node_removed_by_autoscaler'

  def execute(self):
    """Checks for Cluster Autoscaler ScaleDown logs."""
    project = op.get(flags.PROJECT_ID)
    location = op.get(flags.LOCATION)
    node = op.get(flags.NODE)
    name = op.get(flags.NAME)
    project_path = crm.get_project(project)

    filter_str = [
        'resource.type="k8s_cluster"',
        'log_id("container.googleapis.com/cluster-autoscaler-visibility")',
        f'jsonPayload.decision.scaleDown.nodesToBeRemoved.node.name="{node}"'
    ]
    if location:
      filter_str.append(f'resource.labels.location="{location}"')
    if name:
      filter_str.append(f'resource.labels.cluster_name="{name}"')

    filter_str = '\n'.join(filter_str)
    log_entries = local_realtime_query(filter_str)

    if log_entries and LOG_DELETED:
      op.add_failed(project_path,
                    reason=op.prep_msg(op.FAILURE_REASON, node=node),
                    remediation=op.prep_msg(op.FAILURE_REMEDIATION))
    else:
      op.add_ok(project_path, reason=op.prep_msg(op.SUCCESS_REASON, node=node))


class NodePoolUpgrade(runbook.Step):
  """Checks if the node was removed by Cluster Upgrade Operation."""

  template = 'nodeunavailability::node_pool_upgrade'

  def execute(self):
    """Checks for Node Upgrade operation logs."""
    project = op.get(flags.PROJECT_ID)
    location = op.get(flags.LOCATION)
    node = op.get(flags.NODE)
    name = op.get(flags.NAME)
    project_path = crm.get_project(project)

    filter_str = [
        'resource.type="k8s_cluster"',
        'log_id("cloudaudit.googleapis.com/activity")',
        'protoPayload.methodName="io.k8s.core.v1.nodes.update"',
        'protoPayload.request.metadata.annotations."gke-current-operation":"UPGRADE_NODES"',
        f'protoPayload.resourceName="core/v1/nodes/{node}"'
    ]
    if location:
      filter_str.append(f'resource.labels.location="{location}"')
    if name:
      filter_str.append(f'resource.labels.cluster_name="{name}"')

    filter_str = '\n'.join(filter_str)
    log_entries = local_realtime_query(filter_str)

    if log_entries and LOG_DELETED:
      op.add_failed(project_path,
                    reason=op.prep_msg(op.FAILURE_REASON, node=node),
                    remediation=op.prep_msg(op.FAILURE_REMEDIATION))
    else:
      op.add_ok(project_path, reason=op.prep_msg(op.SUCCESS_REASON, node=node))


class NodeUnavailabilityEnd(runbook.EndStep):
  """Finalizes the diagnostics process for `Node Unavailability`.

  This step prompts the user to confirm satisfaction with the Root Cause Analysis (RCA)
  performed for `Node Unavailability`.

  Depending on the user's response, it may conclude the runbook execution or trigger additional
  steps, such as generating a report of the findings.
  """

  def execute(self):
    """Finalize `Node Unavailability` diagnostics."""
    response = op.prompt(
        kind=op.CONFIRMATION,
        message=
        'Are you satisfied with the `GKE Node Unavailability` RCA performed?')
    if response == op.NO:
      op.info(message=(
          'If no cause for the node\'s unavailability is found, you could try the node-auto-repair'
          ' runbook, which would cover node unavailability due to node repair events.'
      ))
