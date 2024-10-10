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
"""Module containing Dataproc cluster creation diagnostic tree and custom steps."""

import json
from datetime import datetime

from gcpdiag import runbook
from gcpdiag.queries import (crm, dataproc, gce, iam, logs, network,
                             networkmanagement)
from gcpdiag.runbook import op
from gcpdiag.runbook.crm import generalized_steps as crm_gs
from gcpdiag.runbook.dataproc import flags
from gcpdiag.runbook.iam import generalized_steps as iam_gs


class ClusterCreation(runbook.DiagnosticTree):
  """Provides a comprehensive analysis of common issues which affect Dataproc cluster creation.

  This runbook focuses on a range of potential problems for Dataproc clusters on
  Google Cloud Platform. By conducting a series of checks, the runbook aims to
  pinpoint the root cause of cluster creation difficulties.

  The following areas are examined:

  - Stockout errors: Evaluates Logs Explorer logs regarding stockout in the
  region/zone.

  - Quota availability: Checks for the quota availability in Dataproc cluster project.

  - Network configuration: Performs GCE Network Connectivity Tests, checks \
necessary firewall rules, external/internal IP configuration.

  - Cross-project configuration: Checks if the service account is not in the same
  project and reviews additional
    roles and organization policies enforcement.

  - Shared VPC configuration: Checks if the Dataproc cluster uses a Shared VPC network and
  evaluates if right service account roles are added.

  - Init actions script failures: Evaluates Logs Explorer
  logs regarding init actions script failures or timeouts.
  """

  parameters = {
      flags.PROJECT_ID: {
          'type': str,
          'help': 'The Project ID where the Dataproc cluster is located',
          'required': True,
      },
      flags.CLUSTER_NAME: {
          'type': str,
          'help': ('Dataproc cluster Name of an existing/active resource'),
          'required': True,
      },
      flags.REGION: {
          'type': str,
          'help': 'Dataproc cluster Region',
          'required': True,
      },
      flags.CLUSTER_UUID: {
          'type': str,
          'help': 'Dataproc cluster UUID',
          #'required': True, cannot be required due
          # to limitations on Dataproc API side
      },
      flags.PROJECT_NUMBER: {
          'type': str,
          'help': 'The Project Number where the Dataproc cluster is located',
      },
      flags.SERVICE_ACCOUNT: {
          'type':
              str,
          'help':
              ('Dataproc cluster Service Account used to create the resource'),
      },
      flags.CONSTRAINT: {
          'type':
              bool,
          'help': ('Checks if the Dataproc cluster has an enforced organization'
                   ' policy constraint'),
      },
      flags.STACKDRIVER: {
          'type': str,
          'help': ('Checks if stackdriver logging is enabled for further'
                   ' troubleshooting'),
          'default': True,
      },
      flags.ZONE: {
          'type': str,
          'help': 'Dataproc cluster Zone',
      },
      flags.NETWORK: {
          'type': str,
          'help': 'Dataproc cluster Network',
      },
      flags.SUBNETWORK: {
          'type': str,
          'help': 'Dataproc cluster Subnetwork',
      },
      flags.INTERNAL_IP_ONLY: {
          'type':
              bool,
          'help': ('Checks if the Dataproc cluster has been created with only'
                   ' Internal IP'),
      },
      flags.START_TIME_UTC: {
          'type': datetime,
          'help': 'Start time of the issue',
      },
      flags.END_TIME_UTC: {
          'type': datetime,
          'help': 'End time of the issue',
      },
      flags.CROSS_PROJECT_ID: {
          'type':
              str,
          'help':
              ('Cross Project ID, where service account is located if it is not'
               ' in the same project as the Dataproc cluster'),
      },
      flags.HOST_VPC_PROJECT_ID: {
          'type': str,
          'help': 'Project ID of the Shared VPC network',
      },
  }

  def build_tree(self):
    """Desribes step relationships."""
    # Instantiate your step classes
    quota_check = CheckClusterQuota()
    self.add_start(quota_check)
    # Check if cluster has stockout issue
    stockout_check = CheckClusterStockOut()
    self.add_step(parent=quota_check, child=stockout_check)
    # Check if cluster exist
    cluster_exist = ClusterExists()
    self.add_step(parent=stockout_check, child=cluster_exist)
    # Check if cluster is in error state
    error_check = ClusterInError()
    self.add_step(parent=cluster_exist, child=error_check)
    # Check cluster network configuration
    check_cluster_network = CheckClusterNetwork()
    self.add_step(parent=cluster_exist, child=check_cluster_network)
    # Check if cluster has an Internal IP
    internal_ip_only = InternalIpGateway()
    self.add_step(parent=check_cluster_network, child=internal_ip_only)
    # Check Service Accounts roles
    sa_exists = ServiceAccountExists()
    self.add_step(parent=cluster_exist, child=sa_exists)
    # Check if cluster is on a Shared VPC, if yes, if right role is added
    check_shared_vpc = CheckSharedVPCRoles()
    self.add_step(parent=cluster_exist, child=check_shared_vpc)
    # Check if cluster has init script issue
    init_script_check = CheckInitScriptFailure()
    self.add_step(parent=check_shared_vpc, child=init_script_check)
    self.add_end(ClusterCreationEnd())


class CheckClusterQuota(runbook.StartStep):
  """Verify if the Dataproc cluster has quota issues.

  Checks if the Dataproc cluster had creation issues due to quota.
  """

  template = 'logs_related::cluster_quota'

  def execute(self):
    """Verify cluster quota..."""

    quota_log_match_str = 'Insufficient .* quota'
    cluster_name = op.get(flags.CLUSTER_NAME)
    project = crm.get_project(op.get(flags.PROJECT_ID))

    quota_log_entries = get_log_entries(
        project_id=op.get(flags.PROJECT_ID),
        cluster_name=cluster_name,
        message_filter=f'protoPayload.status.message=~"{quota_log_match_str}"',
        log_id='cloudaudit.googleapis.com/activity',
        start_time_utc=op.get(flags.START_TIME_UTC),
        end_time_utc=op.get(flags.END_TIME_UTC),
    )

    if quota_log_entries:
      op.add_failed(
          project,
          reason=op.prep_msg(op.FAILURE_REASON,
                             cluster_name=op.get(flags.CLUSTER_NAME),
                             project_id=op.get(flags.PROJECT_ID)),
          remediation=op.prep_msg(op.FAILURE_REMEDIATION),
      )
    else:
      op.add_ok(
          project,
          reason=op.prep_msg(
              op.SUCCESS_REASON,
              cluster_name=op.get(flags.CLUSTER_NAME),
              project_id=op.get(flags.PROJECT_ID),
          ),
      )


class CheckClusterStockOut(runbook.Step):
  """Verify if Dataproc cluster has stockout issue.

  Checks if the zone being used to create the cluster has sufficient resources.
  """

  template = 'logs_related::cluster_stockout'

  def execute(self):
    """Verify cluster stockout issue..."""

    err_messages = [
        'ZONE_RESOURCE_POOL_EXHAUSTED',
        'does not have enough resources available to fulfill the request',
        'resource pool exhausted',
        'does not exist in zone',
    ]

    message_filter = '"' + '" OR "'.join(err_messages) + '"'
    cluster_name = op.get(flags.CLUSTER_NAME)
    project = crm.get_project(op.get(flags.PROJECT_ID))

    stockout_filter_log_entries = get_log_entries(
        project_id=op.get(flags.PROJECT_ID),
        cluster_name=cluster_name,
        message_filter=f'protoPayload.status.message=~({message_filter})',
        log_id='cloudaudit.googleapis.com/activity',
        start_time_utc=op.get(flags.START_TIME_UTC),
        end_time_utc=op.get(flags.END_TIME_UTC),
    )

    if stockout_filter_log_entries:
      op.add_failed(project,
                    reason=op.prep_msg(op.FAILURE_REASON,
                                       cluster_name=op.get(flags.CLUSTER_NAME),
                                       project_id=op.get(flags.PROJECT_ID)),
                    remediation=op.prep_msg(op.FAILURE_REMEDIATION))
      self.add_child(ClusterCreationEnd())

    else:
      op.add_ok(
          project,
          reason=op.prep_msg(
              op.SUCCESS_REASON,
              cluster_name=op.get(flags.CLUSTER_NAME),
              project_id=op.get(flags.PROJECT_ID),
          ),
      )


class ClusterExists(runbook.Step):
  """Prepares the parameters required for the dataproc/cluster-creation runbook.

  Ensures both project_id and cluster_name parameters are available.
  """

  template = 'dataproc_attributes::cluster_name_exists'

  def execute(self):
    """Verify cluster exists in Dataproc UI..."""
    project = crm.get_project(op.get(flags.PROJECT_ID))

    if not op.get(flags.CLUSTER_UUID) and not op.get(flags.CLUSTER_NAME):
      op.add_skipped(project,
                     reason='Provide a cluster UUID or name to investigate')
      return
      # uses the API to check for existing cluster based on cluster name
    cluster = dataproc.get_cluster(project=op.get(flags.PROJECT_ID),
                                   region=op.get(flags.REGION),
                                   cluster_name=op.get(flags.CLUSTER_NAME))
    if cluster:
      op.add_ok(
          cluster,
          reason=op.prep_msg(op.SUCCESS_REASON,
                             cluster_name=cluster.name,
                             project_id=project),
      )
      return
    if cluster is None and (not op.get(flags.CLUSTER_UUID) or
                            not op.get(flags.SERVICE_ACCOUNT) or
                            not op.get(flags.NETWORK) or
                            not op.get(flags.SUBNETWORK) or
                            not op.get(flags.INTERNAL_IP_ONLY)):
      op.add_failed(
          project,
          reason=op.prep_msg(
              op.FAILURE_REASON,
              project_id=project,
              cluster_name=op.get(flags.CLUSTER_NAME),
          ),
          remediation=op.prep_msg(op.FAILURE_REMEDIATION),
      )
      self.add_child(ClusterCreationEnd())
      return


class ClusterInError(runbook.Gateway):
  """Verifies if the cluster is in Error state and gathers additional parameters.

  This investigation is needed to identify if the issue is related to cluster
  creation. The issue happens only when the cluster is not able
  to provision successfully and ends up in ERROR state. In this runbook we don't
  investigate RUNNING clusters.
  """

  template = 'dataproc_attributes::error_status'

  def execute(self):
    """Verify cluster is in ERROR state..."""
    # Taking cluster details
    cluster = dataproc.get_cluster(project=op.get(flags.PROJECT_ID),
                                   region=op.get(flags.REGION),
                                   cluster_name=op.get(flags.CLUSTER_NAME))
    # Checking for ERROR state
    if op.get(flags.CLUSTER_UUID):
      op.info(
          'Cluster is in ERROR state or not existing and additional parameters'
          ' has been provided')
      self.add_child(ClusterDetails())
    elif ('ERROR' in cluster.status) or ('RUNNING' not in cluster.status):
      op.put(flags.STATUS, cluster.status)
      op.info(
          'Cluster is in ERROR state or not existing and additional parameters'
          ' has been provided')
      self.add_child(ClusterDetails())
    elif 'RUNNING' in cluster.status:
      op.info(
          'Cluster is in RUNNING state. Please choose another issue category to'
          ' investigate, the issue is not related to cluster creation, as the'
          ' cluster provisioned successfully.')
      self.add_child(ClusterCreationEnd())


class ClusterDetails(runbook.Step):
  """Gathers cluster parameters needed for further investigation.

  Additional parameters are needed for next steps. If values are provided
  manually they will be used instead of values gathered here.
  """

  template = 'dataproc_attributes::stackdriver'

  def execute(self):
    """Gathering cluster details..."""
    # taking cluster details
    cluster = dataproc.get_cluster(project=op.get(flags.PROJECT_ID),
                                   region=op.get(flags.REGION),
                                   cluster_name=op.get(flags.CLUSTER_NAME))

    if cluster is not None or not op.get(flags.CLUSTER_UUID):
      op.put(flags.STACKDRIVER, cluster.is_stackdriver_logging_enabled)
      op.add_ok(cluster, reason=op.prep_msg(op.SUCCESS_REASON))
    else:
      op.add_uncertain(
          cluster,
          reason=op.prep_msg(op.UNCERTAIN_REASON),
          remediation=op.prep_msg(op.UNCERTAIN_REMEDIATION),
      )

    if not op.get(flags.CLUSTER_UUID):
      if cluster.cluster_uuid:
        op.put(flags.CLUSTER_UUID, cluster.cluster_uuid)
      else:
        op.add_skipped(
            cluster,
            reason=(
                "Cluster UUID couldn't be identified, wait for the cluster to"
                ' finish provisioning and use the runbook, when the cluster is'
                ' in ERROR state'),
        )

    if not op.get(flags.SERVICE_ACCOUNT):
      if cluster.vm_service_account_email:
        op.put(flags.SERVICE_ACCOUNT, cluster.vm_service_account_email)
        op.info(('Service Account:{}').format(cluster.vm_service_account_email))

    if not op.get(flags.NETWORK):
      if cluster.gce_network_uri:
        op.put(flags.NETWORK, cluster.gce_network_uri)
        op.info(('Network: {}').format(cluster.gce_network_uri))

    if network.get_network_from_url(op.get(flags.NETWORK)):
      op.put(
          flags.HOST_VPC_PROJECT_ID,
          network.get_network_from_url(op.get(flags.NETWORK)).project_id,
      )


class CheckClusterNetwork(runbook.Step):
  """Verify that the nodes in the cluster can communicate with each other.

  The Compute Engine Virtual Machine instances (VMs) in a Dataproc cluster must
  be able to communicate with each other using ICMP, TCP (all ports), and UDP
  (all ports) protocols.
  """

  template = 'network::cluster_network'

  def execute(self):
    """Verify network connectivity among nodes in the cluster..."""
    # Gathering cluster details...
    cluster = dataproc.get_cluster(project=op.get(flags.PROJECT_ID),
                                   region=op.get(flags.REGION),
                                   cluster_name=op.get(flags.CLUSTER_NAME))
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
          op.info(('Zone: {}').format(cluster.zone))

      # retrieve the zone from the cluster
      cluster_zone = op.get(flags.ZONE)
      if cluster_zone is None:
        op.add_skipped(
            cluster,
            reason=
            (f'Zone cannot be retrieved from the cluster. Zone: {cluster_zone}'
            ),
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
      op.info('Running connectivity tests...')
      # ICMP
      op.info('ICMP test...')
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
      op.info('TCP test...')
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
      op.info('UDP test...')
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


class InternalIpGateway(runbook.Gateway):
  """Check if the cluster is using internal IP only.

  Check if the Dataproc cluster that is isolated from the public internet
  whose VM instances communicate over a private IP subnetwork (cluster VMs are
  not assigned public IP addresses).
  """

  def execute(self):
    """Checking if the cluster is using internal IP only..."""
    # Gathering cluster details...
    cluster = dataproc.get_cluster(project=op.get(flags.PROJECT_ID),
                                   region=op.get(flags.REGION),
                                   cluster_name=op.get(flags.CLUSTER_NAME))
    is_internal_ip_only = None
    # If cluster cannot be found, gather details from flags
    if cluster is None:
      is_internal_ip_only = op.get(flags.INTERNAL_IP_ONLY)
      if is_internal_ip_only is None:
        op.add_skipped(
            cluster,
            'The cluster and the internalIpOnly config cannot be found, skipping this step. '
            + 'Please provide internal_ip_only as input parameter ' +
            'if the cluster is deleted or keep the cluster in error state.')
        return
      subnetwork_uri = op.get(flags.SUBNETWORK)
      if subnetwork_uri is None:
        op.add_skipped(
            cluster,
            'The cluster and the subnetworkUri config cannot be found, skipping this step. '
            + 'Please provide subnetwork_uri as input parameter ' +
            'if the cluster is deleted or keep the cluster in error state.')
        return
    else:
      is_internal_ip_only = cluster.is_internal_ip_only
      subnetwork_uri = cluster.gce_subnetwork_uri
    # Add the related configs of the cluster
    if is_internal_ip_only is not None and subnetwork_uri is not None:
      # Add the internal IP config of the cluster
      if not op.get(flags.INTERNAL_IP_ONLY):
        if cluster.is_internal_ip_only is not None:
          op.put(flags.INTERNAL_IP_ONLY, cluster.is_internal_ip_only)
          op.info(('Internal IP only: {}').format(cluster.is_internal_ip_only),)
      # Add the subnetwork of the cluster
      if not op.get(flags.SUBNETWORK):
        op.put(flags.SUBNETWORK, subnetwork_uri)
        op.add_ok(cluster, reason=('Subnetwork: {}').format(subnetwork_uri))
    # If the cluster is in private subnet, check that PGA is enabled
    # otherwise end this step
    if is_internal_ip_only:
      self.add_child(child=CheckPrivateGoogleAccess())
    else:
      op.add_ok(cluster, reason='The cluster is in a public subnet.')


class CheckPrivateGoogleAccess(runbook.Step):
  """Check if the subnetwork of the cluster has private google access enabled.

  Checking if the subnetwork of the cluster has private google access enabled.
  """

  template = 'network::private_google_access'

  def execute(self):
    """Checking if the subnetwork of the cluster has private google access enabled...."""
    # taking cluster details
    cluster = dataproc.get_cluster(project=op.get(flags.PROJECT_ID),
                                   region=op.get(flags.REGION),
                                   cluster_name=op.get(flags.CLUSTER_NAME))
    subnetwork_uri = op.get(flags.SUBNETWORK)
    subnetwork_obj = network.get_subnetwork_from_url(subnetwork_uri)

    if subnetwork_obj.is_private_ip_google_access():
      op.add_ok(
          cluster,
          reason=op.prep_msg(op.SUCCESS_REASON, subnetwork_uri=subnetwork_uri),
      )

    else:
      op.add_failed(
          cluster,
          reason=op.prep_msg(op.FAILURE_REASON, subnetwork_uri=subnetwork_uri),
          remediation=op.prep_msg(op.FAILURE_REMEDIATION),
      )


class ServiceAccountExists(runbook.Gateway):
  """Validating service account and permissions in Dataproc cluster project or another project.

  Decides whether to check for service account roles
  - in CROSS_PROJECT_ID, if specified by customer
  - in PROJECT_ID
  """

  template = 'permissions::projectcheck'

  def execute(self):
    """Checking service account project..."""
    sa_email = op.get(flags.SERVICE_ACCOUNT)
    project = crm.get_project(op.get(flags.PROJECT_ID))
    op.info(op.get(flags.SERVICE_ACCOUNT))
    sa_exists = iam.is_service_account_existing(email=sa_email,
                                                billing_project_id=op.get(
                                                    flags.PROJECT_ID))
    sa_exists_cross_project = iam.is_service_account_existing(
        email=sa_email, billing_project_id=op.get(flags.CROSS_PROJECT_ID))

    if sa_exists:
      op.info(
          'VM Service Account associated with Dataproc cluster was found in the'
          ' same project')
      op.info('Checking permissions...')
      # Check for Service Account permissions
      sa_permission_check = iam_gs.IamPolicyCheck()
      sa_permission_check.project = op.get(flags.PROJECT_ID)
      sa_permission_check.principal = (
          f'serviceAccount:{op.get(flags.SERVICE_ACCOUNT)}')
      sa_permission_check.require_all = True
      sa_permission_check.roles = ['roles/dataproc.worker']
      self.add_child(child=sa_permission_check)
    elif sa_exists_cross_project:
      op.info('VM Service Account associated with Dataproc cluster was found in'
              ' cross project')
      # Check if constraint is enforced
      op.info('Checking constraints on service account project...')
      orgpolicy_constraint_check = crm_gs.OrgPolicyCheck()
      orgpolicy_constraint_check.project = op.get(flags.CROSS_PROJECT_ID)
      orgpolicy_constraint_check.constraint = (
          'constraints/iam.disableCrossProjectServiceAccountUsage')
      orgpolicy_constraint_check.is_enforced = False
      self.add_child(orgpolicy_constraint_check)

      # Check Service Account roles
      op.info('Checking roles in service account project...')
      sa_permission_check = iam_gs.IamPolicyCheck()
      sa_permission_check.project = op.get(flags.CROSS_PROJECT_ID)
      sa_permission_check.principal = (
          f'serviceAccount:{op.get(flags.SERVICE_ACCOUNT)}')
      sa_permission_check.require_all = True
      sa_permission_check.roles = [
          'roles/iam.serviceAccountUser',
          'roles/dataproc.worker',
      ]
      self.add_child(child=sa_permission_check)

      # Check Service Agent Service Account roles
      op.info('Checking service agent service account roles on service account'
              ' project...')
      # project = crm.get_project(op.get(flags.PROJECT_ID))
      service_agent_sa = (
          f'service-{project.number}@dataproc-accounts.iam.gserviceaccount.com')
      service_agent_permission_check = iam_gs.IamPolicyCheck()
      service_agent_permission_check.project = op.get(flags.CROSS_PROJECT_ID)
      service_agent_permission_check.principal = (
          f'serviceAccount:{service_agent_sa}')
      service_agent_permission_check.require_all = True
      service_agent_permission_check.roles = [
          'roles/iam.serviceAccountUser',
          'roles/iam.serviceAccountTokenCreator',
      ]
      self.add_child(child=service_agent_permission_check)

      # Check Compute Agent Service Account
      op.info('Checking compute agent service account roles on service account'
              ' project...')
      compute_agent_sa = (
          f'service-{project.number}@compute-system.iam.gserviceaccount.com')
      compute_agent_permission_check = iam_gs.IamPolicyCheck()
      compute_agent_permission_check.project = op.get(flags.CROSS_PROJECT_ID)
      compute_agent_permission_check.principal = (
          f'serviceAccount:{compute_agent_sa}')
      compute_agent_permission_check.require_all = True
      compute_agent_permission_check.roles = [
          'roles/iam.serviceAccountTokenCreator'
      ]
      self.add_child(child=compute_agent_permission_check)

    else:
      op.add_failed(project,
                    reason=op.prep_msg(op.FAILURE_REASON,
                                       service_account=op.get(
                                           flags.SERVICE_ACCOUNT),
                                       project_id=op.get(flags.PROJECT_ID)),
                    remediation=op.prep_msg(op.FAILURE_REMEDIATION))


class CheckSharedVPCRoles(runbook.Step):
  """Verify if dataproc cluster is using Shared VPC.

  Checks for missing roles.
  """

  def execute(self):
    """Verify service account roles based on Shared VPC..."""
    project = crm.get_project(op.get(flags.PROJECT_ID))
    if not op.get(flags.HOST_VPC_PROJECT_ID) == op.get(flags.PROJECT_ID):
      #Check Service Agent Service Account role:
      service_agent_sa = f'service-{project.number}@dataproc-accounts.iam.gserviceaccount.com'
      service_agent_vpc_permission_check = iam_gs.IamPolicyCheck()
      service_agent_vpc_permission_check.project = op.get(
          flags.HOST_VPC_PROJECT_ID)
      service_agent_vpc_permission_check.principal = f'serviceAccount:{service_agent_sa}'
      service_agent_vpc_permission_check.require_all = True
      service_agent_vpc_permission_check.roles = ['roles/compute.networkUser']
      self.add_child(child=service_agent_vpc_permission_check)

      #Check Google APIs Service Account
      op.info(
          'Checking Google APIs service account roles on host VPC project...')
      api_sa = f'{project.number}@cloudservices.gserviceaccount.com'
      api_vpc_permission_check = iam_gs.IamPolicyCheck()
      api_vpc_permission_check.project = op.get(flags.HOST_VPC_PROJECT_ID)
      api_vpc_permission_check.principal = f'serviceAccount:{api_sa}'
      api_vpc_permission_check.require_all = True
      api_vpc_permission_check.roles = ['roles/compute.networkUser']
      self.add_child(child=api_vpc_permission_check)
    else:
      op.add_skipped(project,
                     reason='Cluster is not using a Shared VPC network')


class CheckInitScriptFailure(runbook.Step):
  """Verify if dataproc cluster init script failed.

  The initialization action provided during cluster creation failed to install.
  """

  template = 'logs_related::cluster_init'

  def execute(self):
    """Verify Cluster init script failure."""

    init_script_log_match = 'Initialization action failed'
    cluster_name = op.get(flags.CLUSTER_NAME)
    project = crm.get_project(op.get(flags.PROJECT_ID))

    log_search_filter = f"""resource.type="cloud_dataproc_cluster"
    jsonPayload.message=~"{init_script_log_match}"
    resource.labels.cluster_name="{cluster_name}"
    severity=ERROR
    log_id("google.dataproc.agent")"""

    log_entries = logs.realtime_query(
        project_id=op.get(flags.PROJECT_ID),
        filter_str=log_search_filter,
        start_time_utc=op.get(flags.START_TIME_UTC),
        end_time_utc=op.get(flags.END_TIME_UTC),
    )
    if log_entries:
      op.add_failed(
          project,
          reason=op.prep_msg(op.FAILURE_REASON,
                             cluster_name=op.get(flags.CLUSTER_NAME)),
          remediation=op.prep_msg(op.FAILURE_REMEDIATION),
      )
    else:
      op.add_ok(
          project,
          reason=op.prep_msg(
              op.SUCCESS_REASON,
              cluster_name=op.get(flags.CLUSTER_NAME),
              project_id=op.get(flags.PROJECT_ID),
          ),
      )


class ClusterCreationEnd(runbook.EndStep):
  """The end step of the runbook

  Points out all the failed steps to the user.
  """

  def execute(self):
    """This is the end step of the runbook."""
    op.info(
        """Please visit all the FAIL steps and address the suggested remediations.
        If the cluster is still not able to be provisioned successfully,
        run the runbook again and open a Support case. If you are missing
        Service Account permissions, but are not able to see the Service Agent
        Service Account go to the IAM page and check 'Include Google-provided
        role grants'""")


def get_log_entries(
    project_id,
    cluster_name,
    message_filter,
    log_id,
    start_time_utc,
    end_time_utc,
):
  """Get log entries for given parameters.

  Args:
    project_id:
    cluster_name:
    message_filter:
    log_id:
    start_time_utc:
    end_time_utc:

  Returns:
  """
  log_search_filter = f"""
    resource.type="cloud_dataproc_cluster"
    {message_filter}
    resource.labels.cluster_name="{cluster_name}"
    severity=ERROR
    log_id("{log_id}")
    """

  return logs.realtime_query(
      project_id=project_id,
      filter_str=log_search_filter,
      start_time_utc=start_time_utc,
      end_time_utc=end_time_utc,
  )
