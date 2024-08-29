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
from gcpdiag.runbook.gke import flags, util
from gcpdiag.utils import GcpApiError


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
      flags.START_TIME_UTC: {
          'type':
              datetime,
          'help':
              'The start window to investigate the ip exhaustion. Format: YYYY-MM-DDTHH:MM:SSZ'
      },
      flags.END_TIME_UTC: {
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
    gateway = IpExhaustionGateway()
    # Describe the step relationships
    self.add_step(parent=start, child=gateway)
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


class IpExhaustionGateway(runbook.Gateway):
  """Check for IP Exhaustion issue and the cluster configuration type.

  Based the cluster configuration and IP exhaustion type, the diagnostic process
  would be directed towards relevant next steps.
  """

  def execute(self):
    """Checking IP Exhaustion and cluster configuration"""

    cluster = gke.get_cluster(op.get(flags.PROJECT_ID),
                              cluster_id=op.get(flags.NAME),
                              location=op.get(flags.LOCATION))

    # Define the query strings to be used to search cloud logging.
    ip_space_exhausted_query = f'"IP_SPACE_EXHAUSTED" AND "{op.get(flags.NAME)}"'
    ip_space_exhausted_pod_range_query = f'logName="projects/gcpdiag-vpc2-8pk1otam/logs/\
networkanalyzer.googleapis.com%2Fanalyzer_reports" AND \
jsonPayload.resourceName="//container.googleapis.com/projects\
/{op.get(flags.PROJECT_ID)}/zones/{op.get(flags.LOCATION)}/clusters/cluster-1"'

    # Check activity logs if 'IP_SPACE_EXHAUSTED' log is present in cloud logging.
    op.info(
        f'Searching cloud logging for the string {ip_space_exhausted_query} '
        'which indicates IP Exhaustion issue')
    ip_space_exhausted_log_entries = logs.realtime_query(
        project_id=op.get(flags.PROJECT_ID),
        filter_str=ip_space_exhausted_query,
        start_time_utc=op.get(flags.START_TIME_UTC),
        end_time_utc=op.get(flags.END_TIME_UTC))

    # Check cloud log entries and cluster status for IP exhaustion.
    if len(ip_space_exhausted_log_entries) > 0 or 'IP_SPACE_EXHAUSTED' in str(
        cluster.status_message):
      op.info('log entries with IP_SPACE_EXHAUSTED found in cloud logging for '
              f'the cluster {op.get(flags.NAME)}')
      self.add_child(NodeIpRangeExhaustion())

    # Check for exhaustion of pod range
    ip_space_exhausted_pod_range_log_entries = logs.realtime_query(
        project_id=op.get(flags.PROJECT_ID),
        filter_str=ip_space_exhausted_pod_range_query,
        start_time_utc=op.get(flags.START_TIME_UTC),
        end_time_utc=op.get(flags.END_TIME_UTC))

    if util.is_pod_range_exhausted(ip_space_exhausted_pod_range_log_entries):
      self.add_child(PodIpRangeExhaustion())
    else:
      op.add_ok(
          cluster,
          reason=('No IP exhaustion issues found for {} found in project {}'
                 ).format(cluster.name, op.get(flags.PROJECT_ID)))
      self.add_child(IpExhaustionEnd())


class PodIpRangeExhaustion(runbook.Step):
  """Check Pod IP Range Exhaustion and offer remediation.

  Checks Pod IP range exhaustion and offers remediation step.
  """

  template = 'ipexhaustion::pod_ip_exhaustion'

  def execute(self):
    """Checking Pod IP Exhaustion and offering remediation steps"""

    cluster = gke.get_cluster(op.get(flags.PROJECT_ID),
                              cluster_id=op.get(flags.NAME),
                              location=op.get(flags.LOCATION))

    op.info(
        'Verifying if the cluster is an Autopilot cluster or a standard cluster...'
    )

    if cluster.is_autopilot:
      op.info('Cluster is an Autopilot cluster')
      op.add_failed(cluster,
                    reason=op.prep_msg(op.FAILURE_REASON,
                                       cluster_type='Autopilot',
                                       cluster_name=op.get(flags.NAME)),
                    remediation=op.prep_msg(op.FAILURE_REMEDIATION))
    else:
      op.info('Cluster is a standard cluster')
      op.add_failed(cluster,
                    reason=op.prep_msg(op.FAILURE_REASON,
                                       cluster_type='Standard',
                                       cluster_name=op.get(flags.NAME)),
                    remediation=op.prep_msg(op.FAILURE_REMEDIATION))


class NodeIpRangeExhaustion(runbook.Step):
  """Check Node IP Range Exhaustion and offer remediation.

  Checks Node IP range exhaustion and offers remediation step.
  """

  template = 'ipexhaustion::node_ip_exhaustion'

  def execute(self):
    """Checking node IP Exhaustion and offering remediation steps"""

    cluster = gke.get_cluster(op.get(flags.PROJECT_ID),
                              cluster_id=op.get(flags.NAME),
                              location=op.get(flags.LOCATION))
    op.info(
        'Checking the cluster status message if IP Exhaustion issue is ongoing...'
    )

    if cluster.status_message and 'IP_SPACE_EXHAUSTED' in cluster.status_message:
      op.add_failed(cluster,
                    reason=op.prep_msg(op.FAILURE_REASON,
                                       cluster_type='Standard',
                                       cluster_name=op.get(flags.NAME),
                                       status_message=cluster.status_message),
                    remediation=op.prep_msg(op.FAILURE_REMEDIATION))
    else:
      op.add_ok(cluster,
                reason=op.prep_msg(op.SUCCESS_REASON, cluster_type='Standard'))


class IpExhaustionEnd(runbook.EndStep):
  """Concludes the CLuster IP Exhaustion diagnostics process.

  If the issue persists, it directs the user to helpful
  resources and suggests contacting support with a detailed report.
  """

  def execute(self):
    """Finalizing VM external connectivity diagnostics..."""

    if not config.get(flags.INTERACTIVE_MODE):
      response = op.prompt(
          kind=op.CONFIRMATION,
          message=
          f'Are you still experiencing exhaustion issues on the cluster {op.get(flags.NAME)}',
          choice_msg='Enter an option: ')
      if response == op.NO:
        op.info(message=op.END_MESSAGE)
