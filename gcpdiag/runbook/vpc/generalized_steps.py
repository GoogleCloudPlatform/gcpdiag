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
"""Contains Reusable Steps for VPC related Diagnostic Trees"""

import json

from gcpdiag import runbook
from gcpdiag.queries import gce, networkmanagement
from gcpdiag.runbook import op
from gcpdiag.runbook.vpc import flags, util


class VpcFirewallCheck(runbook.Step):
  """Checks if ingress or egress traffic is allowed to a GCE Instance from a specified source IP.

  Evaluates VPC firewall rules to verify if a GCE Instance permits ingress or egress traffic from a
  designated source IP through a specified port and protocol.
  """
  traffic = None

  def execute(self):
    """Evaluating VPC network firewall rules."""
    vm = gce.get_instance(project_id=op.get(flags.PROJECT_ID),
                          zone=op.get(flags.ZONE),
                          instance_name=op.get(flags.NAME))

    result = None
    if self.traffic == 'ingress':
      result = vm.network.firewall.check_connectivity_ingress(
          src_ip=op.get(flags.SRC_IP),
          ip_protocol=op.get(flags.PROTOCOL_TYPE),
          port=op.get(flags.PORT),
          target_service_account=vm.service_account,
          target_tags=vm.tags)

    if self.traffic == 'egress':
      result = vm.network.firewall.check_connectivity_egress(
          src_ip=op.get(flags.DEST_IP),
          ip_protocol=op.get(flags.PROTOCOL_TYPE),
          port=op.get(flags.DEST_PORT),
          target_service_account=vm.service_account,
          target_tags=vm.tags)

    if result.action == 'deny':
      op.add_failed(vm,
                    reason=op.prep_msg(op.FAILURE_REASON,
                                       address=op.get(flags.DEST_IP),
                                       protocol=op.get(flags.PROTOCOL_TYPE),
                                       port=op.get(flags.PORT),
                                       name=vm.name,
                                       result=result.matched_by_str),
                    remediation=op.prep_msg(op.FAILURE_REMEDIATION))
    elif result.action == 'allow':
      op.add_ok(
          vm,
          op.prep_msg(op.SUCCESS_REASON,
                      address=op.get(flags.SRC_IP),
                      protocol=op.get(flags.PROTOCOL_TYPE),
                      port=op.get(flags.PORT),
                      name=vm.name,
                      result=result.matched_by_str))


class VpcRouteCheck(runbook.Step):
  """Checks VPC route for routing rule exists to the destination IP address.

  Evaluates the VPC routing rules for the most specific route that
  - matches the destination IP address on the VPC route selection order.
  """

  def execute(self):
    """Evaluating the VPC routing rules."""
    vm = gce.get_instance(project_id=op.get(flags.PROJECT_ID),
                          zone=op.get(flags.ZONE),
                          instance_name=op.get(flags.NAME))
    # get project, network info from nic
    nic_info = util.get_nic_info(vm.get_network_interfaces,
                                 op.get(flags.SRC_NIC))

    project, netwrk, dest_ip = nic_info['project'], nic_info['network'], op.get(
        flags.DEST_IP)
    # get the selected route for the destination
    selected_route = util.get_selected_route_for_dest_ip(
        project, netwrk, dest_ip)

    if selected_route:
      # check that the selected route has a next hop destination set to
      # default Internet Gateway if interface has an external IP
      next_hop = selected_route.get_next_hop()
      if next_hop['type'] == 'nextHopGateway':
        op.add_ok(
            vm, op.prep_msg(op.SUCCESS_REASON, route_name=selected_route.name))
      else:
        next_hop_link = next_hop['link']
        op.add_uncertain(vm,
                         reason=op.prep_msg(op.UNCERTAIN_REASON,
                                            address=op.get(flags.DEST_IP),
                                            next_hop_link=next_hop_link,
                                            route_name=selected_route.name),
                         remediation=op.prep_msg(op.UNCERTAIN_REMEDIATION))
    else:
      op.add_failed(vm,
                    reason=op.prep_msg(op.FAILURE_REASON,
                                       address=op.get(flags.DEST_IP)),
                    remediation=op.prep_msg(op.FAILURE_REMEDIATION))


class VmExternalIpConnectivityTest(runbook.Step):
  """Runs a network connectivity test from VM to a destination endpoint.

  Evaluates the connectivity test for any issues and reports to the user."""

  def execute(self):
    """Running a connectivity test to the external ip address."""
    vm = gce.get_instance(project_id=op.get(flags.PROJECT_ID),
                          zone=op.get(flags.ZONE),
                          instance_name=op.get(flags.NAME))

    dest_ip = op.get(flags.DEST_IP)
    dest_ip = dest_ip.exploded

    result = networkmanagement.run_connectivity_test(
        op.get(flags.PROJECT_ID), op.get(flags.SRC_IP), dest_ip,
        op.get(flags.DEST_PORT), op.get(flags.PROTOCOL_TYPE))
    # if the VM has only a private IP address, check that there is a NATGW in
    # the traffic path and put the NATGW details
    if result and not util.is_external_ip_on_nic(vm.get_network_interfaces,
                                                 op.get(flags.SRC_NIC)):
      steps = result['reachabilityDetails']['traces'][0]['steps']
      if 'CLOUD_NAT' in str(steps):
        natgw_step = [
            step for step in steps
            if step.get('nat', {}).get('type', {}) == 'CLOUD_NAT'
        ]
        op.put('nat_gateway_name', natgw_step[0]['nat']['natGatewayName'])
        op.put('nat_gateway_uri', natgw_step[0]['nat']['routerUri'])
      else:
        # the VM has only a private IP address but there is no NATGW in the traffic path
        # Notify the cx if a custom NAT GW is being used.
        op.add_uncertain(vm,
                         reason="""
          A NAT gateway is not found in the external traffic path for the VM: {},
          connecting to the external IP address {}.
          """.format(op.get(flags.NAME), dest_ip),
                         remediation="""
          If a VM instance or custom NAT is being used as a NAT Gateway, check that
          it is configured and functioning correctly. Otherwise, ensure that a public
          Cloud NAT is configured for the VPC Network [1]:

          Check that the destination IP is a Google Service IP address and
          Private Google Access is enabled

          1. https://cloud.google.com/nat/docs/set-up-manage-network-address-translation#creating_nat
          """)

    # If there is no result from the connectivity test, prompt to rerun/retest
    if not result:
      response = op.prompt(
          kind=op.HUMAN_TASK,
          message='The connectivity test did not run successfully: No result '
          'returned. Do you want to rerun the connectivity test?',
          choice_msg='Enter an option: ')
      if response == op.STOP:
        op.add_skipped(vm, reason='Skipping the connectivity test.')

    # Report the connectivity test result
    result_status = result.get('reachabilityDetails', {}).get('result')

    # Clean up the connectivity test

    # Log the connectivity test steps
    description = 'description'
    state = 'state'

    for step in result['reachabilityDetails']['traces'][0]['steps']:
      op.info(f'{step[state]} -> {step[description]}')

    if result_status == 'REACHABLE':
      op.add_ok(
          vm,
          op.prep_msg(op.SUCCESS_REASON,
                      address=op.get(flags.DEST_IP).exploded,
                      result_status=result_status,
                      trace=str(json.dumps(result['reachabilityDetails']))))
    elif result_status in ('AMBIGUOUS', 'UNDETERMINED'):
      op.add_uncertain(
          vm,
          op.prep_msg(op.UNCERTAIN_REASON,
                      address=op.get(flags.DEST_IP).exploded,
                      result_status=result_status,
                      trace=str(json.dumps(result['reachabilityDetails']))),
          remediation=op.prep_msg(op.UNCERTAIN_REMEDIATION))
    else:
      op.add_failed(vm,
                    op.prep_msg(op.FAILURE_REASON,
                                address=op.get(flags.DEST_IP).exploded,
                                result_status=result_status,
                                trace=str(
                                    json.dumps(result['reachabilityDetails']))),
                    remediation=op.prep_msg(op.UNCERTAIN_REMEDIATION))
