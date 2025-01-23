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

import ipaddress

import googleapiclient.errors

from gcpdiag import config, runbook
from gcpdiag.queries import crm, gce
from gcpdiag.runbook import op
from gcpdiag.runbook.gcp import generalized_steps as gcp_gs
from gcpdiag.runbook.nat import generalized_steps as nat_gs
from gcpdiag.runbook.vpc import flags
from gcpdiag.runbook.vpc import generalized_steps as vpc_gs
from gcpdiag.runbook.vpc import util

SCOPE_TO_SINGLE_VM = 'vm_exists'


class VmExternalIpConnectivity(runbook.DiagnosticTree):
  """Troubleshooting for common issues which affect VM connectivity to external IP addresses.

  This runbook investigates components required for VMs to establish connectivity
  to external IP addresses

  Areas Examined:

  - VM Instance:
      - Verify that the VM exists and is running

  - VM Configuration:
      - Checks the source nic configuration on the VM if it has an
        External IP address or not.

  - VPC routes checks:
      - Checks the VPC routing rules are configured to allow external connectivity

  - VPC firewall and firewall policy checks:
      - Checks the VPC firewall and firewall policies allow external connectivity.

  - GCE Network Connectivity Tests:
      - Runs a VPC network connectivity test and reports the result.

  - NATGW Checks:
      - For source nics without an External IP address, verify the VM is served
        by a Public NAT Gateway and check there are no issues on the NATGW.
    """

  parameters = {
      flags.PROJECT_ID: {
          'type': str,
          'help': 'The Project ID of the resource under investigation',
          'required': True
      },
      flags.NAME: {
          'type': str,
          'help': 'The name of the GCE Instance',
          'group': 'instance',
          'required': True
      },
      flags.DEST_IP: {
          'type': ipaddress.IPv4Address,
          'help': 'External IP the VM is connecting to',
          'required': True
      },
      flags.DEST_PORT: {
          'type': int,
          'help': 'External IP the VM is connecting to',
          'default': 443
      },
      flags.PROTOCOL_TYPE: {
          'type': str,
          'help': 'Protocol used to connect to SSH',
          'default': 'tcp',
      },
      flags.SRC_NIC: {
          'type': str,
          'help': 'VM source NIC',
          'required': True
      },
      flags.ZONE: {
          'type': str,
          'help': 'The zone of the target GCE Instance',
          'required': True
      }
  }

  def build_tree(self):
    """Construct the diagnostic tree with appropriate steps."""
    # Instantiate step classes
    start = VmExternalIpConnectivityStart()
    has_external_ip = VmHasExternalIp()
    # Check that the networkmanagement api is enabled
    service_api_status_check = gcp_gs.ServiceApiStatusCheck()
    service_api_status_check.api_name = 'networkmanagement'
    service_api_status_check.expected_state = gcp_gs.constants.APIState.ENABLED

    # add to the debugging tree
    self.add_start(start)
    # Describe the step relationships
    self.add_step(parent=start, child=service_api_status_check)
    self.add_step(parent=service_api_status_check, child=has_external_ip)
    # Ending your runbook
    self.add_end(VmExternalIpConnectivityEnd())


class VmExternalIpConnectivityStart(runbook.StartStep):
  """Start VM external connectivity checks"""

  def execute(self):
    """Starting VM external connectivity diagnostics"""
    project = crm.get_project(op.get(flags.PROJECT_ID))
    try:
      vm = gce.get_instance(project_id=op.get(flags.PROJECT_ID),
                            zone=op.get(flags.ZONE),
                            instance_name=op.get(flags.NAME))
    except googleapiclient.errors.HttpError:
      op.add_skipped(
          project,
          reason=('Instance {} does not exist in zone {} or project {}').format(
              op.get(flags.NAME), op.get(flags.ZONE), op.get(flags.PROJECT_ID)))
    else:
      if vm:
        # Check for instance id and instance name
        if not op.get(flags.ID):
          op.put(flags.ID, vm.id)

    # Check that the user passed in a valid source NIC on the VM
    if not util.is_valid_nic(op.get(flags.SRC_NIC)):
      op.add_failed(
          vm,
          reason=
          (f'{op.get(flags.SRC_NIC)} is not a valid nic on the the VM {vm.name}.'
          ),
          remediation='Run using a valid nic.')
    else:
      # get the networkIP of the NIC
      for interface in vm.get_network_interfaces:
        if interface['name'] == op.get(flags.SRC_NIC):
          network_ip = interface['networkIP']
          op.put(flags.SRC_IP, network_ip)

    # Check that the user has provided a valid external IP address.
    if op.get(flags.DEST_IP):
      if ipaddress.IPv4Address(op.get(flags.DEST_IP)).is_private:
        op.add_failed(
            op.get(flags.DEST_IP),
            reason=
            f'{op.get(flags.DEST_IP)} is not a public/external ip address.',
            remediation='Run using a valid public/external ip address.')

    # Check that the user has provided a port number
    if not op.get(flags.DEST_PORT):
      op.add_failed(
          op.get(flags.DEST_PORT),
          reason=f'{op.get(flags.DEST_PORT)} is not a valid port address.',
          remediation='Run using a valid destination port.')


class VmHasExternalIp(runbook.Gateway):
  """Checks if the source NIC provided has an external IP address or not.

  Based on the source NIC, IP address type, diagnostic process would be directed towards
  troubleshooting NATGW or direct external connectivity
  """

  def execute(self):
    """Checking if the source NIC has an associated external IP address."""

    vm = gce.get_instance(project_id=op.get(flags.PROJECT_ID),
                          zone=op.get(flags.ZONE),
                          instance_name=op.get(flags.NAME))

    # If this an interface without an external IP address run checks for external interface
    if util.is_external_ip_on_nic(vm.get_network_interfaces,
                                  op.get(flags.SRC_NIC)):
      op.info(
          f'The source NIC {op.get(flags.SRC_NIC)} on the VM has an External IP address,'
          f'checking direct connectivity to external IP {op.get(flags.DEST_IP)}'
      )
      self.add_child(ExternalInterfaceCheck())
    else:
      op.info(
          f'The source NIC {op.get(flags.SRC_NIC)} on the VM does not have an External IP address,'
          f'checking connectivity to external IP {op.get(flags.DEST_IP)} via a NATGW'
      )
      self.add_child(InternalInterfaceCheck())


class VmExternalIpConnectivityEnd(runbook.EndStep):
  """Concludes the VM External IP connectivity diagnostics process.

  If external connectivity issues persist, it directs the user to helpful
  resources and suggests contacting support with a detailed report.
  """

  def execute(self):
    """Finalize VM external connectivity diagnostics."""
    if not config.get(flags.INTERACTIVE_MODE):
      response = op.prompt(kind=op.CONFIRMATION,
                           message="""
          Are you able to connect to external IP from the VM {}:
          after taking the remediation steps outlined.
          """.format(op.get(flags.NAME)),
                           choice_msg='Enter an option: ')
      if response == op.NO:
        op.info(message=op.END_MESSAGE)


class ExternalInterfaceCheck(runbook.CompositeStep):
  """Check connectivity to external endpoint when the VM has an external IP address.

  This step checks firewall and routing rules exist to allow for connectivity to the
  external IP address. It also runs and reports a connectivity test.
  """

  def execute(self):
    """Checking for connectivity from NIC with external IP address."""

    # Check there is egress rule permitting egress traffic to the destination/remote IP
    if op.get(flags.DEST_IP):
      dest_ip_egress_firewall_check = vpc_gs.VpcFirewallCheck()
      dest_ip_egress_firewall_check.traffic = 'egress'
      dest_ip_egress_firewall_check.template = 'vm_external_ip_connectivity::firewall_exists'
      self.add_child(dest_ip_egress_firewall_check)
      # Check VPC routes that routing rule to default internet gateway exists
      dest_route_check = vpc_gs.VpcRouteCheck()
      dest_route_check.template = 'vm_external_ip_connectivity::vpc_route_check_for_nexthop_gateway'
      self.add_child(dest_route_check)
      # run a connectivity test to the external IP address from the VM source IP address.
      connectivity_test = vpc_gs.VmExternalIpConnectivityTest()
      connectivity_test.template = 'vm_external_ip_connectivity::connectivity_test'
      self.add_child(connectivity_test)
      self.add_child(VmExternalIpConnectivityEnd())


class InternalInterfaceCheck(runbook.CompositeStep):
  """Check connectivity to external endpoint when the VM source NIC is an internal interface.

  This step checks firewall and routing rules exist to allow for connectivity to the external
  IP address. It also runs and reports a connectivity test.
  """

  def execute(self):
    """Checking for connectivity from NIC with only a private IP address."""

    # Check there is egress rule permitting egress traffic to the destination/remote IP.
    if op.get(flags.DEST_IP):

      # check the VPC Firewall rules.
      dest_ip_egress_firewall_check = vpc_gs.VpcFirewallCheck()
      dest_ip_egress_firewall_check.traffic = 'egress'
      dest_ip_egress_firewall_check.template = 'vm_external_ip_connectivity::firewall_exists'
      self.add_child(dest_ip_egress_firewall_check)

      # Check VPC routes that routing rule to default internet gateway exists.
      dest_route_check = vpc_gs.VpcRouteCheck()
      dest_route_check.template = 'vm_external_ip_connectivity::vpc_route_check_for_nexthop_gateway'
      self.add_child(dest_route_check)

      # run a connectivity test to the external IP address from the VM source IP address.
      connectivity_test = vpc_gs.VmExternalIpConnectivityTest()
      connectivity_test.template = 'vm_external_ip_connectivity::connectivity_test'
      self.add_child(connectivity_test)

      # run a connectivity test to the external IP address from the VM source IP address.
      nat_ip_exhaustion_check = nat_gs.NatIpExhaustionCheck()
      self.add_child(nat_ip_exhaustion_check)

      # run resource exhaustion check to for OUT_OF_RESOURCES or ENDPOINT_INDEPENDENCE_CONFLICT.
      nat_resource_exhaustion_check = nat_gs.NatResourceExhaustionCheck()
      self.add_child(nat_resource_exhaustion_check)

      # Check received packet dropped count metric on the NATGW level for elevated count.
      nat_dropped_received_packet_check = nat_gs.NatDroppedReceivedPacketCheck()
      self.add_child(nat_dropped_received_packet_check)

      # End the diagnostic tree.
      self.add_child(VmExternalIpConnectivityEnd())
