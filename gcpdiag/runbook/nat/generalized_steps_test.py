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
"""Reusable Steps for NAT related Diagnostic Trees"""

import datetime
import unittest
from unittest import mock

from gcpdiag.queries import apis_stub
from gcpdiag.runbook import op
from gcpdiag.runbook.nat import generalized_steps
from gcpdiag.runbook.vpc import flags


class MockMessage:
  """Mock messages for testing.

  Simply returns the key to verify template usage.
  """

  def get_msg(self, key, **kwargs):
    del kwargs
    return f'{key}'


class MockMonitoringResult:

  def __init__(self, data):
    self._data = data

  def values(self):
    return self._data

  def __bool__(self):
    return bool(self._data)


def make_ip_exhaustion_result(is_failed):
  if is_failed is None:
    return None
  return MockMonitoringResult([{'values': [[is_failed]]}])


def make_resource_exhaustion_result(value, reason='OUT_OF_RESOURCES'):
  if value is None:
    return None
  return MockMonitoringResult([{
      'values': [[value]],
      'labels': {
          'metric.reason': reason
      }
  }])


def make_dropped_received_packet_result(value):
  if value is None:
    return None
  return MockMonitoringResult([{'values': [[value]]}])


def make_vm_dropped_received_packet_result(vm_drops):
  # vm_drops is a list of tuples: (instance_id, drop_count)
  data = []
  for instance_id, drop_count in vm_drops:
    data.append({
        'values': [[drop_count]],
        'labels': {
            'resource.instance_id': instance_id
        }
    })
  return MockMonitoringResult(data)


class NatStepsTest(unittest.TestCase):

  def setUp(self):
    super().setUp()
    self.enterContext(
        mock.patch('gcpdiag.queries.apis.get_api', new=apis_stub.get_api_stub))
    self.mock_monitoring_query = self.enterContext(
        mock.patch('gcpdiag.queries.monitoring.query'))
    self.mock_region_from_zone = self.enterContext(
        mock.patch('gcpdiag.runbook.nat.utils.region_from_zone',
                   return_value='us-central1'))

    self.mock_interface = mock.create_autospec(op.InteractionInterface,
                                               instance=True)
    self.mock_interface.rm = mock.Mock()
    self.operator = op.Operator(self.mock_interface)
    self.operator.run_id = 'test-run'
    self.operator.messages = MockMessage()
    self.params = {
        flags.PROJECT_ID:
            'gcpdiag-nat1-aaaa',
        flags.ZONE:
            'us-central1-a',
        flags.INSTANCE_NAME:
            'instance-1',
        'nat_gateway_name':
            'nat-gw-1',
        'start_time':
            datetime.datetime(2025, 1, 1, 0, 0, 0,
                              tzinfo=datetime.timezone.utc),
        'end_time':
            datetime.datetime(2025, 1, 1, 1, 0, 0,
                              tzinfo=datetime.timezone.utc),
    }

  def test_nat_ip_exhaustion_check_failed(self):
    self.mock_monitoring_query.return_value = make_ip_exhaustion_result(
        is_failed=True)
    step = generalized_steps.NatIpExhaustionCheck()
    with op.operator_context(self.operator):
      self.operator.parameters = self.params
      self.operator.set_step(step)
      step.execute()
    self.mock_interface.add_failed.assert_called_once()
    self.mock_interface.add_ok.assert_not_called()
    self.mock_interface.add_uncertain.assert_not_called()

  def test_nat_ip_exhaustion_check_ok(self):
    self.mock_monitoring_query.return_value = make_ip_exhaustion_result(
        is_failed=False)
    step = generalized_steps.NatIpExhaustionCheck()
    with op.operator_context(self.operator):
      self.operator.parameters = self.params
      self.operator.set_step(step)
      step.execute()
    self.mock_interface.add_failed.assert_not_called()
    self.mock_interface.add_ok.assert_called_once()
    self.mock_interface.add_uncertain.assert_not_called()

  def test_nat_ip_exhaustion_check_no_gw_name(self):
    self.params['nat_gateway_name'] = None
    step = generalized_steps.NatIpExhaustionCheck()
    with op.operator_context(self.operator):
      self.operator.parameters = self.params
      self.operator.set_step(step)
      step.execute()
    self.mock_interface.add_failed.assert_not_called()
    self.mock_interface.add_ok.assert_not_called()
    self.mock_interface.add_uncertain.assert_called_once()

  def test_nat_ip_exhaustion_check_no_monitoring_data(self):
    self.mock_monitoring_query.return_value = make_ip_exhaustion_result(
        is_failed=None)
    step = generalized_steps.NatIpExhaustionCheck()
    with op.operator_context(self.operator):
      self.operator.parameters = self.params
      self.operator.set_step(step)
      step.execute()
    self.mock_interface.add_ok.assert_not_called()
    self.mock_interface.add_failed.assert_not_called()
    self.mock_interface.add_uncertain.assert_not_called()


class NatResourceExhaustionCheckTest(NatStepsTest):

  def test_nat_resource_exhaustion_check_failed(self):
    self.mock_monitoring_query.return_value = make_resource_exhaustion_result(
        value=1)
    step = generalized_steps.NatResourceExhaustionCheck()
    with op.operator_context(self.operator):
      self.operator.parameters = self.params
      self.operator.set_step(step)
      step.execute()
    self.mock_interface.add_failed.assert_called_once()
    self.mock_interface.add_ok.assert_not_called()
    self.mock_interface.add_uncertain.assert_not_called()

  def test_nat_resource_exhaustion_check_ok(self):
    self.mock_monitoring_query.return_value = make_resource_exhaustion_result(
        value=0)
    step = generalized_steps.NatResourceExhaustionCheck()
    with op.operator_context(self.operator):
      self.operator.parameters = self.params
      self.operator.set_step(step)
      step.execute()
    self.mock_interface.add_failed.assert_not_called()
    self.mock_interface.add_ok.assert_called_once()
    self.mock_interface.add_uncertain.assert_not_called()

  def test_nat_resource_exhaustion_check_no_gw_name(self):
    self.params['nat_gateway_name'] = None
    step = generalized_steps.NatResourceExhaustionCheck()
    with op.operator_context(self.operator):
      self.operator.parameters = self.params
      self.operator.set_step(step)
      step.execute()
    self.mock_interface.add_failed.assert_not_called()
    self.mock_interface.add_ok.assert_not_called()
    self.mock_interface.add_uncertain.assert_called_once()

  def test_nat_resource_exhaustion_check_no_monitoring_data(self):
    self.mock_monitoring_query.return_value = make_resource_exhaustion_result(
        None)
    step = generalized_steps.NatResourceExhaustionCheck()
    with op.operator_context(self.operator):
      self.operator.parameters = self.params
      self.operator.set_step(step)
      step.execute()
    self.mock_interface.add_ok.assert_not_called()
    self.mock_interface.add_failed.assert_not_called()
    self.mock_interface.add_uncertain.assert_not_called()


class NatDroppedReceivedPacketCheckTest(NatStepsTest):

  def test_nat_dropped_received_packet_check_ok(self):
    self.mock_monitoring_query.return_value = make_dropped_received_packet_result(
        0)
    step = generalized_steps.NatDroppedReceivedPacketCheck()
    with op.operator_context(self.operator):
      self.operator.parameters = self.params
      self.operator.set_step(step)
      step.execute()
      self.assertNotIn('natgw_rcv_pkt_drops', self.operator.parameters)
    self.mock_interface.add_failed.assert_not_called()
    self.mock_interface.add_ok.assert_called_once()
    self.mock_interface.add_uncertain.assert_not_called()

  def test_nat_dropped_received_packet_check_no_gw_name(self):
    self.params['nat_gateway_name'] = None
    step = generalized_steps.NatDroppedReceivedPacketCheck()
    with op.operator_context(self.operator):
      self.operator.parameters = self.params
      self.operator.set_step(step)
      step.execute()
      self.assertNotIn('natgw_rcv_pkt_drops', self.operator.parameters)
    self.mock_interface.add_failed.assert_not_called()
    self.mock_interface.add_ok.assert_not_called()
    self.mock_interface.add_uncertain.assert_called_once()

  def test_nat_dropped_received_packet_check_no_monitoring_data(self):
    self.mock_monitoring_query.return_value = make_dropped_received_packet_result(
        None)
    step = generalized_steps.NatDroppedReceivedPacketCheck()
    with op.operator_context(self.operator):
      self.operator.parameters = self.params
      self.operator.set_step(step)
      step.execute()
      self.assertNotIn('natgw_rcv_pkt_drops', self.operator.parameters)
    self.mock_interface.add_ok.assert_not_called()
    self.mock_interface.add_failed.assert_not_called()
    self.mock_interface.add_uncertain.assert_not_called()

  def test_nat_dropped_received_packet_check_gw_drops_no_vm_drops_data(self):
    self.mock_monitoring_query.side_effect = [
        make_dropped_received_packet_result(1), None
    ]
    step = generalized_steps.NatDroppedReceivedPacketCheck()
    with op.operator_context(self.operator):
      self.operator.parameters = self.params
      self.operator.set_step(step)
      step.execute()
      self.assertEqual(op.get('natgw_rcv_pkt_drops'), True)
    self.mock_interface.add_failed.assert_not_called()
    self.mock_interface.add_ok.assert_not_called()
    self.mock_interface.add_uncertain.assert_called_once()

  def test_nat_dropped_received_packet_check_gw_drops_vm_drops_below_threshold(
      self):
    self.mock_monitoring_query.side_effect = [
        make_dropped_received_packet_result(1),
        make_vm_dropped_received_packet_result([('vm1', 0.5), ('vm2', 0)])
    ]
    step = generalized_steps.NatDroppedReceivedPacketCheck()
    with op.operator_context(self.operator):
      self.operator.parameters = self.params
      self.operator.set_step(step)
      step.execute()
      self.assertEqual(op.get('natgw_rcv_pkt_drops'), True)
    self.mock_interface.add_failed.assert_not_called()
    self.mock_interface.add_ok.assert_called_once()
    self.assertEqual(self.mock_interface.add_uncertain.call_count, 1)

  def test_nat_dropped_received_packet_check_gw_drops_with_vm_drops(self):
    self.mock_monitoring_query.side_effect = [
        make_dropped_received_packet_result(1),
        make_vm_dropped_received_packet_result([('vm1', 2), ('vm2', 0)])
    ]
    step = generalized_steps.NatDroppedReceivedPacketCheck()
    with op.operator_context(self.operator):
      self.operator.parameters = self.params
      self.operator.set_step(step)
      step.execute()
      self.assertEqual(op.get('natgw_rcv_pkt_drops'), True)
    self.mock_interface.add_failed.assert_not_called()
    self.mock_interface.add_ok.assert_not_called()
    self.assertEqual(self.mock_interface.add_uncertain.call_count, 2)
