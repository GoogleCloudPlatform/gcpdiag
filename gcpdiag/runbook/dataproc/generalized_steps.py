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
"""Contains Generatlized Steps for Dataproc."""

import json

from gcpdiag import runbook
from gcpdiag.queries import crm, dataproc, gce, logs, networkmanagement
from gcpdiag.runbook import op
from gcpdiag.runbook.dataproc import flags


class CheckLogsExist(runbook.Step):
  """Checks if specified logs messages exist in the Dataproc cluster.

  This step supports checking for the presence of a concrete log message.

  Attributes:
    log_message (str): log message that is being looked for.
  """
  template = 'logs_related::default'
  log_message: str = ''
  cluster_name: str = ''
  cluster_uuid: str = ''
  project_id: str = ''

  def execute(self):
    """Check if investigated logs messages exist in the Dataproc cluster."""

    if not self.project_id:
      project = crm.get_project(op.get(flags.PROJECT_ID))
    else:
      project = crm.get_project(self.project_id)

    if op.get(flags.JOB_EXIST) == 'false':
      op.add_skipped(project, reason="Job doesn't exist, skipping this step.")
      return

    if op.get(flags.JOB_OLDER_THAN_30_DAYS):
      op.add_skipped(
          project,
          reason=('Job is older than 30 days, skipping this step. '
                  'Please create a new job and run the runbook again.'),
      )
      return

    if not (self.cluster_name and self.cluster_uuid):
      job = dataproc.get_job_by_jobid(op.get(flags.PROJECT_ID),
                                      op.get(flags.REGION),
                                      op.get(flags.JOB_ID))

      cluster_name = job.cluster_name
      cluster_uuid = job.cluster_uuid
    else:
      cluster_name = self.cluster_name
      cluster_uuid = self.cluster_uuid

    job_id = op.get(flags.JOB_ID)
    log_message = self.log_message

    log_search_filter = f"""resource.type="cloud_dataproc_cluster"
    resource.labels.cluster_name="{cluster_name}"
    resource.labels.cluster_uuid="{cluster_uuid}"
    "{job_id}"
    jsonPayload.message=~"{log_message}" """

    start_time = op.get(flags.START_TIME)
    end_time = op.get(flags.END_TIME)

    log_entries = logs.realtime_query(
        project_id=op.get(flags.PROJECT_ID),
        filter_str=log_search_filter,
        start_time=start_time,
        end_time=end_time,
    )

    if log_entries:
      op.add_failed(
          project,
          reason=op.prep_msg(op.FAILURE_REASON,
                             log=log_message,
                             cluster_name=cluster_name),
          remediation=op.prep_msg(op.FAILURE_REMEDIATION),
      )
    else:
      op.add_ok(
          project,
          reason=op.prep_msg(
              op.SUCCESS_REASON,
              log=log_message,
              cluster_name=cluster_name,
          ),
      )


class CheckClusterNetworkConnectivity(runbook.Step):
  """Verify that the nodes in the cluster can communicate with each other.

  The Compute Engine Virtual Machine instances (VMs) in a Dataproc cluster must
  be able to communicate with each other using ICMP, TCP (all ports), and UDP
  (all ports) protocols.
  """

  template = 'network::cluster_network'
  cluster_name: str = ''
  project_id: str = ''

  def execute(self):
    """Verify network connectivity among nodes in the cluster."""
    # Gathering cluster details.

    if not self.project_id:
      project_id = op.get(flags.PROJECT_ID)
    else:
      project_id = self.project_id

    if not self.cluster_name:
      cluster_name = op.get(flags.CLUSTER_NAME)
    else:
      cluster_name = self.cluster_name

    cluster = dataproc.get_cluster(cluster_name=cluster_name,
                                   region=op.get(flags.REGION),
                                   project=project_id)

    # Skip this step if the cluster does not exist
    if cluster is None:
      op.add_uncertain(cluster,
                       reason=op.prep_msg(op.UNCERTAIN_REASON),
                       remediation=op.prep_msg(op.UNCERTAIN_REMEDIATION))
    else:
      # Add the zone of the cluster
      if not op.get(flags.ZONE):
        if cluster.zone:
          op.put(flags.ZONE, cluster.zone)

      # retrieve the zone from the cluster
      cluster_zone = op.get(flags.ZONE)
      if cluster_zone is None:
        op.add_skipped(
            cluster,
            reason=(
                'Zone cannot be retrieved from the cluster.Please provide the'
                ' ZONE parameter in the runbook query'),
        )
        return
      # Skip DPGKE clusters
      if not cluster.is_gce_cluster:
        op.add_skipped(
            cluster,
            reason='This is a Dataproc on GKE cluster, skipping this step.',
        )
      # Skip single node clusters
      if cluster.is_single_node_cluster:
        op.add_skipped(
            cluster,
            reason='This is a single node cluster, skipping this step.')
      # target (master node or master node 0)
      if cluster.is_ha_cluster:
        target = gce.get_instance(
            project_id=op.get(flags.PROJECT_ID),
            zone=cluster_zone,
            instance_name=f'{cluster.name}-m-0',
        )
      else:
        target = gce.get_instance(
            project_id=op.get(flags.PROJECT_ID),
            zone=cluster_zone,
            instance_name=f'{cluster.name}-m',
        )
      target_ip = target.get_network_ip_for_instance_interface(
          cluster.gce_network_uri)
      # source (worker node 0)
      source = gce.get_instance(
          project_id=op.get(flags.PROJECT_ID),
          zone=cluster_zone,
          instance_name=f'{cluster.name}-w-0',
      )
      source_ip = source.get_network_ip_for_instance_interface(
          cluster.gce_network_uri)

      is_connectivity_fine = True

      # run connectivity tests between master and worker
      op.info('Running connectivity tests.')
      # ICMP
      op.info('ICMP test.')
      connectivity_test_result = networkmanagement.run_connectivity_test(
          project_id=op.get(flags.PROJECT_ID),
          src_ip=str(source_ip)[:-3],
          dest_ip=str(target_ip)[:-3],
          dest_port=None,
          protocol='ICMP')
      op.info('Connectivity test result: ' +
              connectivity_test_result['reachabilityDetails']['result'])
      if connectivity_test_result['reachabilityDetails'][
          'result'] != 'REACHABLE':
        is_connectivity_fine = False
        for trace in connectivity_test_result['reachabilityDetails']['traces']:
          op.info('Endpoint details: ' +
                  json.dumps(trace['endpointInfo'], indent=2))
          last_step = None
          for step in trace['steps']:
            last_step = step
          op.info('Last step: ' + json.dumps(last_step, indent=2))
          op.info('Full list of steps: ' + json.dumps(trace['steps'], indent=2))
        op.info(
            'ICMP traffic must be allowed. Check the result of the connectivity '
            + 'test to verify what is blocking the traffic, ' +
            'in particular Last step and Full list of steps.')
      # TCP
      op.info('TCP test.')
      connectivity_test_result = networkmanagement.run_connectivity_test(
          project_id=op.get(flags.PROJECT_ID),
          src_ip=str(source_ip)[:-3],
          dest_ip=str(target_ip)[:-3],
          dest_port=8088,
          protocol='TCP')
      op.info('Connectivity test result: ' +
              connectivity_test_result['reachabilityDetails']['result'])
      if connectivity_test_result['reachabilityDetails'][
          'result'] != 'REACHABLE':
        is_connectivity_fine = False
        for trace in connectivity_test_result['reachabilityDetails']['traces']:
          op.info('Endpoint details: ' +
                  json.dumps(trace['endpointInfo'], indent=2))
          last_step = None
          for step in trace['steps']:
            last_step = step
          op.info('Last step: ' + json.dumps(last_step, indent=2))
          op.info('Full list of steps: ' + json.dumps(trace['steps'], indent=2))
        op.info(
            'TCP traffic must be allowed. Check the result of the connectivity test'
            + 'to verify what is blocking the traffic, ' +
            'in particular Last step and Full list of steps.')
      # UCP
      op.info('UDP test.')
      connectivity_test_result = networkmanagement.run_connectivity_test(
          project_id=op.get(flags.PROJECT_ID),
          src_ip=str(source_ip)[:-3],
          dest_ip=str(target_ip)[:-3],
          dest_port=8088,
          protocol='UDP')
      op.info('Connectivity test result: ' +
              connectivity_test_result['reachabilityDetails']['result'])
      if connectivity_test_result['reachabilityDetails'][
          'result'] != 'REACHABLE':
        is_connectivity_fine = False
        for trace in connectivity_test_result['reachabilityDetails']['traces']:
          op.info('Endpoint details: ' +
                  json.dumps(trace['endpointInfo'], indent=2))
          last_step = None
          for step in trace['steps']:
            last_step = step
          op.info('Last step: ' + json.dumps(last_step, indent=2))
          op.info('Full list of steps: ' + json.dumps(trace['steps'], indent=2))
        op.info(
            'UDP traffic must be allowed. Check the result of the connectivity test '
            + 'to verify what is blocking the traffic, ' +
            'in particular Last step and Full list of steps.')

      if is_connectivity_fine:
        op.add_ok(cluster,
                  op.prep_msg(op.SUCCESS_REASON, cluster_name=cluster.name))
      else:
        op.add_failed(
            cluster,
            reason=op.prep_msg(op.FAILURE_REASON, cluster_name=cluster.name),
            remediation=op.prep_msg(op.FAILURE_REMEDIATION),
        )
