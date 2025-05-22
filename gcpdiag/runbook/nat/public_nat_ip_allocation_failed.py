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
"""Module containing NAT IP Allocation Failed debugging tree and custom steps"""

import googleapiclient.errors

from gcpdiag import config, runbook
from gcpdiag.queries import crm, monitoring, network
from gcpdiag.runbook import op
from gcpdiag.runbook.nat import flags


class PublicNatIpAllocationFailed(runbook.DiagnosticTree):
  """Troubleshooting for IP Allocation issues for Cloud NAT.

  This runbook investigates Cloud NAT for NAT IP Allocation failed issue and proposes
  remediation steps.

  Areas Examined:

    - Metric check: Checks the NAT Allocation Failed metric for the provided NATGW if it is
    True or False.

    - NATGW Configuration: Checks the gateway if it is configured with manual or automatic IP
    allocation.

    - NAT IP and Port calculation: For source nic without an External IP address,
      verify the VM is served by a Public NAT Gateway and check there are no issues on the NATGW.
    """

  parameters = {
      flags.PROJECT_ID: {
          'type': str,
          'help': 'The Project ID of the resource under investigation',
          'required': True
      },
      flags.NAT_GATEWAY_NAME: {
          'type': str,
          'help': 'The name of the NATGW',
          'required': True
      },
      flags.CLOUD_ROUTER_NAME: {
          'type': str,
          'help': 'The name of the Cloud Router of the NATGW',
          'required': True
      },
      flags.NETWORK: {
          'type': str,
          'help': 'The VPC network of the target NATGW',
          'new_parameter': 'nat_network',
          'deprecated': True,
      },
      flags.NAT_NETWORK: {
          'type': str,
          'help': 'The VPC network of the target NATGW',
          'required': True
      },
      flags.REGION: {
          'type': str,
          'help': 'The region of the target NATGW',
          'required': True
      }
  }

  def legacy_parameter_handler(self, parameters):
    """Handles legacy parameters."""
    if flags.NETWORK in parameters:
      parameters[flags.NAT_NETWORK] = parameters.pop(flags.NETWORK)

  def build_tree(self):
    """Construct the diagnostic tree with appropriate steps."""
    # Instantiate step classes
    start = NatIpAllocationFailedStart()
    nat_allocation_failed_check = NatAllocationFailedCheck()
    nat_gw_ip_allocation_method_check = NatIpAllocationMethodCheck()

    # add to the debugging tree
    self.add_start(start)
    # Describe the step relationships
    self.add_step(parent=start, child=nat_allocation_failed_check)
    self.add_step(parent=nat_allocation_failed_check,
                  child=nat_gw_ip_allocation_method_check)
    # Ending your runbook
    self.add_end(NatIpAllocationFailedEnd())


class NatIpAllocationFailedStart(runbook.StartStep):
  """Start Nat IP Allocation Failed Checks.


  This step steps starts the NAT IP Allocation Failed Check debugging process by
  verifying the correct input parameters have been provided and checking to ensure
  that the following resources exist.
    - The Project
    - VPC Network
    - The NAT Cloud Router
  """

  template = 'nat_ip_allocation_failed::confirmation'

  def execute(self):
    """Starting Nat IP Allocation Failed diagnostics"""
    project = crm.get_project(op.get(flags.PROJECT_ID))
    # try to fetch the network for the NATGW
    try:
      vpc_network = network.get_network(
          project_id=op.get(flags.PROJECT_ID),
          network_name=op.get(flags.NAT_NETWORK),
      )
    except googleapiclient.errors.HttpError:
      op.add_skipped(
          project,
          reason=op.prep_msg(
              op.SKIPPED_REASON,
              network=op.get(flags.NAT_NETWORK),
              project_id=op.get(flags.PROJECT_ID),
          ),
      )
      return
    # try to get the cloud router
    try:
      routers = network.get_routers(
          project_id=op.get(flags.PROJECT_ID),
          region=op.get(flags.REGION),
          network=vpc_network,
      )
    except googleapiclient.errors.HttpError:
      op.add_skipped(
          project,
          reason=op.prep_msg(
              op.SKIPPED_REASON_ALT1,
              cloud_router=op.get(flags.CLOUD_ROUTER_NAME),
              region=op.get(flags.REGION),
              project_id=op.get(flags.PROJECT_ID),
          ),
      )
    if routers:
      # Check that the cloud router name passed is valid.
      router = [r for r in routers if r.name == op.get(flags.CLOUD_ROUTER_NAME)]
      if not router:
        op.add_skipped(
            project,
            reason=op.prep_msg(
                op.SKIPPED_REASON_ALT2,
                cloud_router=op.get(flags.CLOUD_ROUTER_NAME),
                region=op.get(flags.REGION),
                project_id=op.get(flags.PROJECT_ID),
            ),
        )
      # Check that the natgateway name passed is served by the cloud router.
      nat_router = router[0]
      if not [
          n for n in nat_router.nats
          if n['name'] == op.get(flags.NAT_GATEWAY_NAME)
      ]:
        op.add_skipped(
            project,
            reason=op.prep_msg(
                op.SKIPPED_REASON_ALT3,
                cloud_router=op.get(flags.NAT_GATEWAY_NAME),
                region=op.get(flags.REGION),
                project_id=op.get(flags.PROJECT_ID),
            ),
        )


class NatAllocationFailedCheck(runbook.Step):
  """Checks NAT Allocation failed metric for the NATGW.

  This step determines whether Cloud NAT has run into issues due to insufficient
  NAT IP addresses.
  by checking the NAT Allocation failed metric.
  """

  template = 'nat_ip_allocation_failed::nat_allocation_metric_check'

  def execute(self):
    """Checking the nat_allocation_failed metric for NAT IP allocation failure
      and the NAT router status.
    """

    project = crm.get_project(op.get(flags.PROJECT_ID))

    gw_name = op.get(flags.NAT_GATEWAY_NAME)
    region = op.get(flags.REGION)
    # check the nat router status
    router_status = network.nat_router_status(
        project_id=op.get(flags.PROJECT_ID),
        router_name=op.get(flags.CLOUD_ROUTER_NAME),
        region=op.get(flags.REGION))
    if not router_status:
      op.info('unable to fetch router status for the router: %s',
              op.get(flags.CLOUD_ROUTER_NAME))
    else:
      min_extra_ips_needed = router_status.min_extra_nat_ips_needed
      vms_with_nat_mappings = router_status.num_vms_with_nat_mappings

    nat_allocation_failed = monitoring.query(
        op.get(flags.PROJECT_ID),
        'fetch nat_gateway::router.googleapis.com/nat/nat_allocation_failed '
        f'| filter (resource.gateway_name == \'{gw_name}\' && resource.region == \'{region}\')'
        ' | within 5m')

    if nat_allocation_failed:
      values = nat_allocation_failed.values()
      for value in values:
        if value.get('values')[0][0] or min_extra_ips_needed:
          op.add_failed(project,
                        reason=op.prep_msg(
                            op.FAILURE_REASON,
                            nat_gateway_name=op.get(flags.NAT_GATEWAY_NAME),
                            router_name=op.get(flags.CLOUD_ROUTER_NAME),
                            min_extra_ips_needed=min_extra_ips_needed,
                            vms_with_nat_mappings=vms_with_nat_mappings),
                        remediation=op.prep_msg(
                            op.FAILURE_REMEDIATION,
                            nat_gateway_name=op.get(flags.NAT_GATEWAY_NAME),
                            router_name=op.get(flags.CLOUD_ROUTER_NAME),
                            min_extra_ips_needed=min_extra_ips_needed,
                            vms_with_nat_mappings=vms_with_nat_mappings))
        else:
          op.add_ok(project,
                    reason=op.prep_msg(
                        op.SUCCESS_REASON,
                        nat_gateway_name=op.get(flags.NAT_GATEWAY_NAME),
                        router_name=op.get(flags.CLOUD_ROUTER_NAME),
                        min_extra_ips_needed=min_extra_ips_needed,
                        vms_with_nat_mappings=vms_with_nat_mappings))
          op.add_skipped(project,
                         reason=op.prep_msg(
                             op.SKIPPED_REASON,
                             nat_gateway_name=op.get(flags.NAT_GATEWAY_NAME),
                             router_name=op.get(flags.CLOUD_ROUTER_NAME)))
    else:
      op.add_uncertain(project,
                       reason=op.prep_msg(op.UNCERTAIN_REASON,
                                          nat_gateway_name=op.get(
                                              flags.NAT_GATEWAY_NAME)),
                       remediation=op.prep_msg(op.UNCERTAIN_REMEDIATION,
                                               nat_gateway_name=op.get(
                                                   flags.NAT_GATEWAY_NAME)))


class NatIpAllocationMethodCheck(runbook.Gateway):
  """Checks the NATGW configuration to determine next troubleshooting steps.

  Checks if the NATGW router is configured with manual or automatic IP allocation
  """

  template = 'nat_ip_allocation_failed::nat_allocation_method_check'

  def execute(self):
    """Checking the NATGW configuration."""

    project = crm.get_project(op.get(flags.PROJECT_ID))

    # try to fetch the network for the NATGW
    try:
      vpc_network = network.get_network(project_id=op.get(flags.PROJECT_ID),
                                        network_name=op.get(flags.NAT_NETWORK))
    except googleapiclient.errors.HttpError:
      op.add_skipped(
          project,
          reason=
          ("""Unable to fetch the network {} confirm it exists in the project {}"""
          ).format(op.get(flags.NAT_NETWORK), op.get(flags.PROJECT_ID)))
      return
    # try to get the router
    try:
      routers = network.get_routers(project_id=op.get(flags.PROJECT_ID),
                                    region=op.get(flags.REGION),
                                    network=vpc_network)
    except googleapiclient.errors.HttpError:
      op.add_skipped(project,
                     reason=("""Failed to fetch routers in the vpc network {}
                  does not exist in region {} of project {}""").format(
                         op.get(flags.NAT_NETWORK), op.get(flags.REGION),
                         op.get(flags.PROJECT_ID)))

    if routers:
      # filter routers for the cloud router name specified for the gateway.
      router = [r for r in routers if r.name == op.get(flags.CLOUD_ROUTER_NAME)]
      if router:
        nat_router = router[0]
        if nat_router.get_nat_ip_allocate_option(
            nat_gateway=op.get(flags.NAT_GATEWAY_NAME)) == 'AUTO_ONLY':
          self.add_child(NatIpAllocationAutoOnly())
        else:
          self.add_child(NatIpAllocationManualOnly())
      else:
        op.add_skipped(project,
                       reason="""
          No Cloud router with the name: {} found.
          """.format(op.get(flags.CLOUD_ROUTER_NAME)))


class NatIpAllocationAutoOnly(runbook.Step):
  """Provides recommendations when NAT IP allocation is AUTO_ONLY.

  NAT IP allocation is configured as AUTO_ONLY, either:
    - Switch to Manual NAT IP assignment or
    - Add one more gateway in the same network and region
  """

  template = 'nat_ip_allocation_failed::nat_allocation_auto_only'

  def execute(self):
    """NAT IP allocation is configured as AUTO_ONLY."""
    project = crm.get_project(op.get(flags.PROJECT_ID))

    op.add_failed(project,
                  reason=op.prep_msg(op.FAILURE_REASON,
                                     nat_gateway_name=op.get(
                                         flags.NAT_GATEWAY_NAME)),
                  remediation=op.prep_msg(op.FAILURE_REMEDIATION))


class NatIpAllocationManualOnly(runbook.Step):
  """Investigates when NAT IP allocation is MANUAL_ONLY.

  If the NAT IP allocation is configured as MANUAL_ONLY:
    - Confirm if the number of NAT IP's required by the gateway is over 300
    - Follow the NAT IP Quota Increase Process
  """

  template = 'nat_ip_allocation_failed::nat_allocation_manual_only'

  def execute(self):
    """NAT IP allocation is configured with MANUAL_ONLY.

    Running diagnostic for NAT Gateway configured as MANUAL_ONLY only
    """
    project = crm.get_project(op.get(flags.PROJECT_ID))
    enable_dynamic_port_allocation = None
    nat_gw_ips_in_use = None
    min_extra_ips_needed = None
    vms_with_nat_mappings = None

    # try to fetch the network for the NATGW
    try:
      vpc_network = network.get_network(project_id=op.get(flags.PROJECT_ID),
                                        network_name=op.get(flags.NAT_NETWORK))
    except googleapiclient.errors.HttpError:
      op.add_skipped(
          project,
          reason=
          ("""Unable to fetch the network {} confirm it exists in the project {}"""
          ).format(op.get(flags.NAT_NETWORK), op.get(flags.PROJECT_ID)))
      return
    # try to get the router
    try:
      routers = network.get_routers(project_id=op.get(flags.PROJECT_ID),
                                    region=op.get(flags.REGION),
                                    network=vpc_network)
    except googleapiclient.errors.HttpError:
      op.add_skipped(project,
                     reason=("""Failed to fetch routers in the vpc network {}
                  does not exist in region {} of project {}""").format(
                         op.get(flags.NAT_NETWORK), op.get(flags.REGION),
                         op.get(flags.PROJECT_ID)))
    if routers:
      # filter for the cloud router name specified.
      router = [r for r in routers if r.name == op.get(flags.CLOUD_ROUTER_NAME)]
      if router:
        nat_router = router[0]
        enable_dynamic_port_allocation = nat_router.get_enable_dynamic_port_allocation(
            op.get(flags.NAT_GATEWAY_NAME))
    else:
      op.add_skipped(project,
                     reason=("""
          No Cloud router with the name: {} found.
          """).format(op.get(flags.CLOUD_ROUTER_NAME)))

    # Check the nat router status for number of additional NAT IP addresses needed
    router_status = network.nat_router_status(
        project_id=op.get(flags.PROJECT_ID),
        router_name=op.get(flags.CLOUD_ROUTER_NAME),
        region=op.get(flags.REGION))
    if not router_status:
      op.info('unable to fetch router status for the router: %s',
              op.get(flags.CLOUD_ROUTER_NAME))
    else:
      min_extra_ips_needed = router_status.min_extra_nat_ips_needed
      vms_with_nat_mappings = router_status.num_vms_with_nat_mappings

    # get the NAT IP info mappings for the NAT Gateway
    router_nat_ip_info = network.get_nat_ip_info(
        project_id=op.get(flags.PROJECT_ID),
        router_name=op.get(flags.CLOUD_ROUTER_NAME),
        region=op.get(flags.REGION))

    result = router_nat_ip_info.result

    if result and op.get(flags.NAT_GATEWAY_NAME) in str(result):
      nat_gw_ip_info = [
          n for n in result if n['natName'] == op.get(flags.NAT_GATEWAY_NAME)
      ]
      nat_gw_ip_mappings = nat_gw_ip_info[0]['natIpInfoMappings']
      nat_gw_ips_in_use = len(
          [ip for ip in nat_gw_ip_mappings if ip['usage'] == 'IN_USE'])

    op.add_ok(project,
              reason=op.prep_msg(
                  op.SUCCESS_REASON,
                  router_name=op.get(flags.CLOUD_ROUTER_NAME),
                  extra_ips_needed=min_extra_ips_needed,
                  vms_with_nat_mappings=vms_with_nat_mappings,
                  enable_dynamic_port_allocation=enable_dynamic_port_allocation,
                  nat_gw_ips_in_use=nat_gw_ips_in_use))

    if min_extra_ips_needed > 0 and nat_gw_ips_in_use > 299:
      op.add_failed(project,
                    reason=op.prep_msg(op.FAILURE_REASON),
                    remediation=op.prep_msg(op.FAILURE_REMEDIATION))

    if min_extra_ips_needed > 0 and nat_gw_ips_in_use < 300:
      op.add_ok(project,
                reason=op.prep_msg(op.SUCCESS_REASON_ALT1,
                                   nat_gateway_name=op.get(
                                       flags.NAT_GATEWAY_NAME)))


class NatIpAllocationFailedEnd(runbook.EndStep):
  """Concludes the NAT IP allocation failed diagnostics process.

  If NAT allocation issues persist, it directs the user to helpful
  resources and suggests contacting support with a detailed report.
  """

  template = 'nat_ip_allocation_failed::endstep'

  def execute(self):
    """Finalize NAT allocation failed diagnostics."""
    if not config.get(flags.INTERACTIVE_MODE):
      response = op.prompt(
          kind=op.CONFIRMATION,
          message='Does the issue persist after taking remediation steps?',
          choice_msg='Enter an option: ')
      if response == op.NO:
        op.info(message=op.END_MESSAGE)
