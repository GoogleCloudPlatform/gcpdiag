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
"""Contains Reusable Steps for NAT related Diagnostic Trees"""

from gcpdiag import runbook
from gcpdiag.queries import gce, monitoring
from gcpdiag.runbook import op
from gcpdiag.runbook.nat import utils
from gcpdiag.runbook.vpc import flags


class NatIpExhaustionCheck(runbook.Step):
  """Evaluates NATGW for NAT IP exhaustion/allocation issues.

  This step determines whether Cloud NAT has run into issues due to insufficient NAT IP addresses.
  """

  template = 'nat_out_of_resources::nat_ip_exhaustion_check'

  def execute(self):
    """Checking  NAT Allocation failed metric for NAT IP allocation failure"""

    vm = gce.get_instance(project_id=op.get(flags.PROJECT_ID),
                          zone=op.get(flags.ZONE),
                          instance_name=op.get(flags.NAME))

    region = utils.region_from_zone(op.get(flags.ZONE))

    if op.get('nat_gateway_name'):
      gw_name = op.get('nat_gateway_name')
      nat_allocation_failed = monitoring.query(
          op.get(flags.PROJECT_ID),
          'fetch nat_gateway::router.googleapis.com/nat/nat_allocation_failed '
          f'| filter (resource.gateway_name == \'{gw_name}\' && resource.region == \'{region}\')'
          ' | within 5m')

      if nat_allocation_failed:
        values = nat_allocation_failed.values()
        for value in values:
          if value.get('values')[0][0]:
            op.add_failed(vm,
                          reason=op.prep_msg(
                              op.FAILURE_REASON,
                              nat_gateway_name=op.get('nat_gateway_name')),
                          remediation=op.prep_msg(
                              op.FAILURE_REMEDIATION,
                              nat_gateway_name=op.get('nat_gateway_name')))
          else:
            op.add_ok(vm,
                      reason=op.prep_msg(
                          op.SUCCESS_REASON,
                          nat_gateway_name=op.get('nat_gateway_name')))
    else:
      op.add_uncertain(
          vm,
          f'Cloud not get IP allocation failed metric for NATGW {op.get("nat_gateway_name")}'
      )


class NatResourceExhaustionCheck(runbook.Step):
  """Evaluates NATGW for OUT_OF_RESOURCES and ENDPOINT_INDEPENDENCE_CONFLICT issues.


  This step determines whether Cloud NAT has run into resource issues.
  """

  template = 'nat_out_of_resources::nat_resource_exhaustion_check'

  def execute(self):
    """Checking NATGW for OUT_OF_RESOURCES or ENDPOINT_INDEPENDENCE_CONFLICT issues"""

    vm = gce.get_instance(project_id=op.get(flags.PROJECT_ID),
                          zone=op.get(flags.ZONE),
                          instance_name=op.get(flags.NAME))

    region = utils.region_from_zone(op.get(flags.ZONE))

    if op.get('nat_gateway_name'):
      gw_name = op.get('nat_gateway_name')
      dropped_sent_packets_count = monitoring.query(
          op.get(flags.PROJECT_ID),
          'fetch nat_gateway::router.googleapis.com/nat/dropped_sent_packets_count '
          f'| filter (resource.gateway_name == \'{gw_name}\' '
          f'&& resource.region == \'{region}\')'
          '| align rate(10m)'
          '| within 10m | group_by [metric.reason],'
          ' [value_dropped_sent_packets_count_aggregate: '
          'aggregate(value.dropped_sent_packets_count)]')

      if dropped_sent_packets_count:
        values = dropped_sent_packets_count.values()
        for value in values:
          if value.get('values')[0][0]:
            op.add_failed(vm,
                          reason=op.prep_msg(
                              op.FAILURE_REASON,
                              metric_reason=value.get('labels',
                                                      {}).get('metric.reason'),
                              nat_gateway_name=op.get('nat_gateway_name')),
                          remediation=op.prep_msg(op.FAILURE_REMEDIATION))
          else:
            op.add_ok(vm,
                      reason=op.prep_msg(
                          op.SUCCESS_REASON,
                          nat_gateway_name=op.get('nat_gateway_name'),
                          metric_reason=value.get('labels',
                                                  {}).get('metric.reason')))
    else:
      op.add_uncertain(
          vm,
          f'Cloud not get dropped sent packets count metric for NATGW {op.get("nat_gateway_name")}'
      )


class NatDroppedReceivedPacketCheck(runbook.Step):
  """Evaluates NATGW received_packets_dropped metric for issues.


  This step determines whether the NATGW is dropping packets. NAT gateways could be dropping
  packets for various reasons; however, the drops are not always indicative of an issue
  """

  template = 'nat_out_of_resources::nat_dropped_received_packet_check'

  def execute(self):
    """Checking NATGW received_packets_dropped metric for elevated drops"""

    vm = gce.get_instance(project_id=op.get(flags.PROJECT_ID),
                          zone=op.get(flags.ZONE),
                          instance_name=op.get(flags.NAME))

    region = utils.region_from_zone(op.get(flags.ZONE))

    if op.get('nat_gateway_name'):
      gw_name = op.get('nat_gateway_name')
      received_packets_dropped = monitoring.query(
          op.get(flags.PROJECT_ID),
          'fetch nat_gateway::router.googleapis.com/nat/dropped_received_packets_count '
          f'| filter (resource.gateway_name == \'{gw_name}\' && resource.region == \'{region}\')'
          '| align rate(5m) | within 5m | group_by [],'
          '[value_dropped_received_packets_count_aggregate:'
          'aggregate(value.dropped_received_packets_count)]')

      if received_packets_dropped:
        values = received_packets_dropped.values()
        for value in values:
          if value.get('values')[0][0] >= 1:

            op.put('natgw_rcv_pkt_drops', True)

            op.add_uncertain(vm,
                             reason=op.prep_msg(
                                 op.UNCERTAIN_REASON,
                                 nat_gateway_name=op.get('nat_gateway_name'),
                                 metric_value=value.get('values')[0][0]),
                             remediation=op.prep_msg(op.UNCERTAIN_REMEDIATION))

            # Also check the for received packet drops at the vm level
            vm_received_packets_dropped_count = monitoring.query(
                op.get(flags.PROJECT_ID),
                'fetch gce_instance::compute.googleapis.com/nat/dropped_received_packets_count '
                f'| filter (resource.gateway_name == \'{gw_name}\' '
                f'&& resource.region == \'{region}\')'
                '| align rate(5m)'
                '| every 5m'
                '| group_by [resource.instance_id], '
                '[value_dropped_received_packets_count_aggregate: '
                'aggregate(value.dropped_received_packets_count)]')

            if vm_received_packets_dropped_count:
              vm_drop_list = []
              vm_values = vm_received_packets_dropped_count.values()
              for vm_value in vm_values:
                if vm_value.get('values')[0][0] >= 1 and len(vm_drop_list) <= 5:
                  vm_drop_list.append({
                      'instance_id':
                          vm_value.get('labels',
                                       {}).get('resource.instance_id'),
                      'rcv_pkt_drp_count':
                          vm_value.get('values')[0][0]
                  })

              if vm_drop_list:
                op.add_uncertain(
                    vm,
                    reason='Elevated received_packet_drop_count metric noticed'
                    f'for following VMs {str(vm_drop_list)}',
                    remediation=
                    """VMs could be dropping packets for various reasons; however,
                    the drops are not always indicative of an issue.
                    See more on troubleshooting cloud NAT and reducing the drops here [1] and [2]:
                    Open a case to GCP Support for justification for the packet drops.
                      [1] https://cloud.google.com/nat/docs/troubleshooting
                      [2] https://cloud.google.com/knowledge/kb
                      /reduce-received-packets-dropped-count-on-cloud-nat-000006744"""
                )
              else:
                op.add_ok(vm, reason=op.prep_msg(op.SUCCESS_REASON))
          else:
            op.add_ok(vm,
                      reason=op.prep_msg(
                          op.SUCCESS_REASON,
                          nat_gateway_name=op.get('nat_gateway_name')))
    else:
      op.add_uncertain(
          vm, 'Cloud not get dropped_received_packets_count'
          f'metric for NATGW {op.get("nat_gateway_name")}')
