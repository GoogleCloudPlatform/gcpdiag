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
"""Module containing VM External IP connectivity debugging tree and custom steps"""

from datetime import datetime

from gcpdiag import config, runbook
from gcpdiag.queries import crm, gke, logs
from gcpdiag.runbook import op
from gcpdiag.runbook.gke import flags
from gcpdiag.utils import GcpApiError


def local_realtime_query(filter_str):
  result = logs.realtime_query(project_id=op.get(flags.PROJECT_ID),
                               start_time_utc=op.get(flags.START_TIME),
                               end_time_utc=op.get(flags.END_TIME),
                               filter_str=filter_str)
  return result


class IpExhaustion(runbook.DiagnosticTree):
  """Troubleshooting ip exhaustion issues on GKE clusters.

  This runbook investigates the gke cluster for ip exhaustion issues and recommends remediation
  steps.

  Areas Examined:
  - GKE cluster type.
  - GKE cluster and nodepool configuration
  - Stackdriver logs
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
              True
      },
      flags.LOCATION: {
          'type': str,
          'help': 'The zone or region of the GKE cluster',
          'required': True
      },
      flags.START_TIME: {
          'type':
              datetime,
          'help':
              'The start window to investigate the ip exhaustion. Format: YYYY-MM-DDTHH:MM:SSZ'
      },
      flags.END_TIME: {
          'type':
              datetime,
          'help':
              'The end window to investigate the ip exhaustion. Format: YYYY-MM-DDTHH:MM:SSZ'
      }
  }

  def build_tree(self):
    """Construct the diagnostic tree with appropriate steps."""

    # Instantiate your step classes
    start = IpExhaustionStart()
    # add them to your tree
    self.add_start(start)
    # you can create custom steps to define unique logic
    pod_ip_range_exhaustion = PodIpRangeExhaustion()
    node_ip_range_exhaustion = NodeIpRangeExhaustion()
    # Describe the step relationships
    self.add_step(parent=start, child=node_ip_range_exhaustion)
    self.add_step(parent=node_ip_range_exhaustion,
                  child=pod_ip_range_exhaustion)
    # Ending your runbook
    self.add_end(IpExhaustionEnd())


class IpExhaustionStart(runbook.StartStep):
  """Start IP Exhaustion Checks"""

  def execute(self):
    """Starting the IP Exhaustion diagnostics"""

    project = crm.get_project(op.get(flags.PROJECT_ID))
    try:
      cluster = gke.get_cluster(op.get(flags.PROJECT_ID),
                                cluster_id=op.get(flags.NAME),
                                location=op.get(flags.LOCATION))
    except GcpApiError:
      op.add_skipped(
          project,
          reason=('Cluster {} does not exist in {} for project {}').format(
              op.get(flags.NAME), op.get(flags.LOCATION),
              op.get(flags.PROJECT_ID)))
    else:
      op.add_ok(project,
                reason=('Cluster {} found in {} for project {}').format(
                    cluster.name, op.get(flags.LOCATION),
                    op.get(flags.PROJECT_ID)))


class NodeIpRangeExhaustion(runbook.Step):
  """Check Node IP Range Exhaustion and offer remediation.

  Checks Node IP range exhaustion and offers remediation step.
  """

  template = 'ipexhaustion::node_ip_exhaustion'
  # max number of characters from the cluster name that will end up in the node name
  MAX_GKE_NAME_LENGTH = 16

  def execute(self):
    """Checking node IP Exhaustion and offering remediation steps"""

    cluster = gke.get_cluster(op.get(flags.PROJECT_ID),
                              cluster_id=op.get(flags.NAME),
                              location=op.get(flags.LOCATION))
    location = op.get(flags.LOCATION)
    name = op.get(flags.NAME)
    error_msg = 'IP_SPACE_EXHAUSTED'
    node_subnet = cluster.get_subnet_name
    # adding fltr variable, because otherwise the filter string will be longer than 100 chars
    fltr = 'protoPayload.status.details.ipSpaceExhausted.networkOrSubnetworkResource.resourceName'

    # using here ':' instead of '=' for 'protoPayload.status.message' because there could be
    # status messages like 'IP_SPACE_EXHAUSTED,IP_SPACE_EXHAUSTED' instead of 'IP_SPACE_EXHAUSTED'
    filter_str = [
        'log_id("cloudaudit.googleapis.com/activity")',
        'protoPayload.methodName="v1.compute.instances.insert"',
        'resource.type="gce_instance"', 'severity=ERROR',
        f'protoPayload.status.message:"{error_msg}"',
        f'protoPayload.resourceName:"{location}"',
        f'protoPayload.resourceName:"{name[:self.MAX_GKE_NAME_LENGTH]}"',
        f'{fltr}="{node_subnet}"'
    ]
    filter_str = '\n'.join(filter_str)

    # Check activity logs if 'IP_SPACE_EXHAUSTED' log is present in cloud logging.
    op.info(f'Searching cloud logging for the string {error_msg} '
            'which indicates IP Exhaustion issue')
    ip_space_exhausted_log_entries = local_realtime_query(filter_str)

    # Check cloud log entries for IP exhaustion.
    if ip_space_exhausted_log_entries:
      op.info(
          f'{error_msg} error found for cluster {name} and subnet {node_subnet}'
      )
      op.add_failed(cluster,
                    reason=op.prep_msg(op.FAILURE_REASON,
                                       cluster_name=name,
                                       node_subnet=node_subnet),
                    remediation=op.prep_msg(op.FAILURE_REMEDIATION,
                                            node_subnet=node_subnet))
    else:
      op.add_ok(cluster,
                reason=op.prep_msg(op.SUCCESS_REASON, cluster_name=name))


class PodIpRangeExhaustion(runbook.Step):
  """Check Pod IP Range Exhaustion and offer remediation.

  Checks Pod IP range exhaustion and offers remediation step.
  """

  template = 'ipexhaustion::pod_ip_exhaustion'
  MAX_GKE_SUBNET_NAME_LENGTH = 15
  MAX_GKE_NAME_LENGTH = 16

  def execute(self):
    """Checking Pod IP Exhaustion and offering remediation steps"""

    cluster = gke.get_cluster(op.get(flags.PROJECT_ID),
                              cluster_id=op.get(flags.NAME),
                              location=op.get(flags.LOCATION))
    project = op.get(flags.PROJECT_ID)
    location = op.get(flags.LOCATION)
    name = op.get(flags.NAME)
    error_msg = 'IP_SPACE_EXHAUSTED'
    node_subnet = cluster.get_subnet_name
    pool_config = cluster.get_nodepool_config
    pool_nr = len(pool_config)
    # adding fltr variable, because otherwise the filter string will be longer than 100 chars
    fltr = 'protoPayload.status.details.ipSpaceExhausted.networkOrSubnetworkResource.resourceName'

    # using here ':' instead of '=' for 'protoPayload.status.message' because there could be
    # status messages like 'IP_SPACE_EXHAUSTED,IP_SPACE_EXHAUSTED' instead of 'IP_SPACE_EXHAUSTED'
    filter_str = [
        'log_id("cloudaudit.googleapis.com/activity")',
        'protoPayload.methodName="v1.compute.instances.insert"',
        'resource.type="gce_instance"', 'severity=ERROR',
        f'protoPayload.status.message:"{error_msg}"',
        f'protoPayload.resourceName:"{location}"',
        f'protoPayload.resourceName:"{name[:self.MAX_GKE_NAME_LENGTH]}"'
    ]

    # creating a pod_ranges list from a set to exclude duplicates
    pod_ranges = list(
        {pool_config[i]['networkConfig']['podRange'] for i in range(pool_nr)})
    # add opening parenthesis to the query
    filter_str.append('(')

    # create the filter for all subnets for all nodepools
    for pod_range in pod_ranges:
      resource = (f'{node_subnet[:self.MAX_GKE_SUBNET_NAME_LENGTH]}-'
                  f'{pod_range[:self.MAX_GKE_SUBNET_NAME_LENGTH]}-')

      # if it's the last element, don't add OR to the filter
      if pod_range == pod_ranges[-1]:
        filter_str.append(f'{fltr}:"{resource}"')
      else:
        filter_str.append(f'{fltr}:"{resource}" OR')

    # add closing parenthesis to the query
    filter_str.append(')')
    filter_str = '\n'.join(filter_str)
    ip_space_exhausted_pod_range_log_entries = local_realtime_query(filter_str)

    if ip_space_exhausted_pod_range_log_entries:
      op.info(
          'Verifying if the cluster is an Autopilot cluster or a Standard cluster.'
      )

      if cluster.is_autopilot:
        op.info('Cluster is an Autopilot cluster')
        op.add_failed(cluster,
                      reason=op.prep_msg(op.FAILURE_REASON, cluster_name=name),
                      remediation=op.prep_msg(op.FAILURE_REMEDIATION))
      else:
        op.info('Cluster is a Standard cluster')
        op.add_failed(cluster,
                      reason=op.prep_msg(op.FAILURE_REASON, cluster_name=name),
                      remediation=op.prep_msg(op.FAILURE_REMEDIATION_ALT1))
    else:
      op.add_ok(
          cluster,
          reason=
          (f'No Pod IP exhaustion issues found for cluster {name} in the project {project}'
          ))


class IpExhaustionEnd(runbook.EndStep):
  """Concludes the CLuster IP Exhaustion diagnostics process.

  If the issue persists, it directs the user to helpful
  resources and suggests contacting support with a detailed report.
  """

  def execute(self):
    """Finalize VM external connectivity diagnostics."""

    if not config.get(flags.INTERACTIVE_MODE):
      response = op.prompt(
          kind=op.CONFIRMATION,
          message=
          f'Are you still experiencing exhaustion issues on the cluster {op.get(flags.NAME)}',
          choice_msg='Enter an option: ')
      if response == op.NO:
        op.info(message=op.END_MESSAGE)
