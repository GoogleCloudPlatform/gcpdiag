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
"""Test class for nat/nat_ip_allocation_failed"""

import datetime
import unittest
from unittest import mock

import googleapiclient

from gcpdiag import config
from gcpdiag.queries import apis_stub, crm
from gcpdiag.runbook import nat, op, snapshot_test_base
from gcpdiag.runbook.nat import flags, public_nat_ip_allocation_failed


class Test(snapshot_test_base.RulesSnapshotTestBase):
  rule_pkg = nat
  runbook_name = 'nat/public-nat-ip-allocation-failed'
  config.init({'auto': True, 'interface': 'cli'})

  rule_parameters = [{
      'project_id': 'gcpdiag-nat1-aaaa',
      'region': 'europe-west4',
      'nat_gateway_name': 'public-nat-gateway',
      'cloud_router_name': 'public-nat-cloud-router',
      'network': 'nat-vpc-network'
  }]


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


class MockRouterStatus:

  def __init__(self, min_extra_nat_ips_needed, num_vms_with_nat_mappings):
    self.min_extra_nat_ips_needed = min_extra_nat_ips_needed
    self.num_vms_with_nat_mappings = num_vms_with_nat_mappings


class MockNatIpInfo:

  def __init__(self, result):
    self.result = result


class MockRouter:
  """Mock network.Router object."""

  def __init__(self,
               name,
               nats,
               ip_allocate_option='MANUAL_ONLY',
               dynamic_ports=False):
    self.name = name
    self.nats = nats
    self._ip_allocate_option = ip_allocate_option
    self._dynamic_ports = dynamic_ports

  def get_nat_ip_allocate_option(self, nat_gateway):
    del nat_gateway
    return self._ip_allocate_option

  def get_enable_dynamic_port_allocation(self, nat_gateway):
    del nat_gateway
    return self._dynamic_ports


class PublicNatIpAllocationFailedTest(unittest.TestCase):

  def setUp(self):
    super().setUp()
    self.mock_monitoring_query = self.enterContext(
        mock.patch('gcpdiag.queries.monitoring.query'))
    self.mock_get_project = self.enterContext(
        mock.patch('gcpdiag.queries.crm.get_project'))
    self.mock_get_network = self.enterContext(
        mock.patch('gcpdiag.queries.network.get_network'))
    self.mock_get_routers = self.enterContext(
        mock.patch('gcpdiag.queries.network.get_routers'))
    self.mock_nat_router_status = self.enterContext(
        mock.patch('gcpdiag.queries.network.nat_router_status'))
    self.mock_get_nat_ip_info = self.enterContext(
        mock.patch('gcpdiag.queries.network.get_nat_ip_info'))
    self.mock_get_api = self.enterContext(
        mock.patch('gcpdiag.queries.apis.get_api', new=apis_stub.get_api_stub))

    self.mock_interface = mock.create_autospec(op.InteractionInterface,
                                               instance=True)
    self.mock_interface.rm = mock.Mock()
    self.operator = op.Operator(self.mock_interface)
    self.operator.run_id = 'test-run'
    self.operator.messages = MockMessage()
    self.params = {
        flags.PROJECT_ID:
            'test-project',
        flags.REGION:
            'us-central1',
        flags.NAT_GATEWAY_NAME:
            'test-nat-gw',
        flags.CLOUD_ROUTER_NAME:
            'test-router',
        flags.NAT_NETWORK:
            'test-network',
        'start_time':
            datetime.datetime(2025, 1, 1, 0, 0, 0,
                              tzinfo=datetime.timezone.utc),
        'end_time':
            datetime.datetime(2025, 1, 1, 1, 0, 0,
                              tzinfo=datetime.timezone.utc),
    }
    self.mock_get_project.return_value = crm.Project({
        'projectId': 'test-project',
        'name': 'projects/123'
    })
    self.mock_get_network.return_value = mock.MagicMock()
    self.op_get_dict = {
        flags.PROJECT_ID: 'test-project',
        'nat_gateway_name': 'test-nat-gw',
    }

  def test_legacy_parameter_handler_network_present(self):
    """Test that legacy 'network' parameter is moved to 'nat_network'."""
    params = {'network': 'legacy-network-value'}
    tree = public_nat_ip_allocation_failed.PublicNatIpAllocationFailed()
    tree.legacy_parameter_handler(params)
    self.assertNotIn('network', params)
    self.assertIn('nat_network', params)
    self.assertEqual(params['nat_network'], 'legacy-network-value')

  def test_start_step_get_network_fails(self):
    """Test start step when get_network throws HttpError."""
    step = public_nat_ip_allocation_failed.NatIpAllocationFailedStart()
    mock_response = mock.Mock()
    mock_response.status = 404
    self.mock_get_network.side_effect = googleapiclient.errors.HttpError(
        mock_response, b'not found')
    with op.operator_context(self.operator):
      self.operator.parameters = self.params
      self.operator.set_step(step)
      step.execute()
    self.mock_interface.add_skipped.assert_called_once()

  def test_start_step_get_routers_fails(self):
    """Test start step when get_routers throws HttpError."""
    step = public_nat_ip_allocation_failed.NatIpAllocationFailedStart()
    mock_response = mock.Mock()
    mock_response.status = 404
    self.mock_get_routers.side_effect = googleapiclient.errors.HttpError(
        mock_response, b'not found')
    with op.operator_context(self.operator):
      self.operator.parameters = self.params
      self.operator.set_step(step)
      step.execute()
    self.mock_interface.add_skipped.assert_called_once()

  def test_start_step_router_not_found(self):
    """Test start step when router name not in list."""
    step = public_nat_ip_allocation_failed.NatIpAllocationFailedStart()
    self.mock_get_routers.return_value = [
        MockRouter('other-router', nats=[{
            'name': 'test-nat-gw'
        }])
    ]
    with op.operator_context(self.operator):
      self.operator.parameters = self.params
      self.operator.set_step(step)
      step.execute()
    self.mock_interface.add_skipped.assert_called_once()

  def test_start_step_nat_gw_not_found(self):
    """Test start step when nat gw name not in router."""
    step = public_nat_ip_allocation_failed.NatIpAllocationFailedStart()
    self.mock_get_routers.return_value = [
        MockRouter('test-router', nats=[{
            'name': 'other-nat-gw'
        }])
    ]
    with op.operator_context(self.operator):
      self.operator.parameters = self.params
      self.operator.set_step(step)
      step.execute()
    self.mock_interface.add_skipped.assert_called_once()

  def test_nat_allocation_failed_check_no_router_status(self):
    """Test allocation check when router status is missing."""
    step = public_nat_ip_allocation_failed.NatAllocationFailedCheck()
    self.mock_nat_router_status.return_value = None
    self.mock_monitoring_query.return_value = make_ip_exhaustion_result(
        is_failed=False)
    with op.operator_context(self.operator):
      self.operator.parameters = self.params
      self.operator.set_step(step)
      step.execute()
    self.mock_interface.add_ok.assert_called_once()
    self.mock_interface.add_skipped.assert_called_once()

  def test_nat_allocation_failed_check_monitoring_returns_none(self):
    """Test allocation check when monitoring returns no data."""
    step = public_nat_ip_allocation_failed.NatAllocationFailedCheck()
    self.mock_nat_router_status.return_value = MockRouterStatus(0, 10)
    self.mock_monitoring_query.return_value = None
    with op.operator_context(self.operator):
      self.operator.parameters = self.params
      self.operator.set_step(step)
      step.execute()
    self.mock_interface.add_uncertain.assert_called_once()

  def test_nat_allocation_failed_check_failed_metric(self):
    """Test allocation check when nat_allocation_failed metric is true."""
    step = public_nat_ip_allocation_failed.NatAllocationFailedCheck()
    self.mock_nat_router_status.return_value = MockRouterStatus(None, 10)
    self.mock_monitoring_query.return_value = make_ip_exhaustion_result(
        is_failed=True)
    with op.operator_context(self.operator):
      self.operator.parameters = self.params
      self.operator.set_step(step)
      step.execute()
    self.mock_interface.add_failed.assert_called_once()

  def test_nat_allocation_failed_check_extra_ips_needed(self):
    """Test allocation check when min_extra_ips_needed > 0."""
    step = public_nat_ip_allocation_failed.NatAllocationFailedCheck()
    self.mock_nat_router_status.return_value = MockRouterStatus(5, 10)
    self.mock_monitoring_query.return_value = make_ip_exhaustion_result(
        is_failed=False)
    with op.operator_context(self.operator):
      self.operator.parameters = self.params
      self.operator.set_step(step)
      step.execute()
    self.mock_interface.add_failed.assert_called_once()

  def test_nat_allocation_failed_check_ok(self):
    """Test allocation check passes."""
    step = public_nat_ip_allocation_failed.NatAllocationFailedCheck()
    self.mock_nat_router_status.return_value = MockRouterStatus(0, 10)
    self.mock_monitoring_query.return_value = make_ip_exhaustion_result(
        is_failed=False)
    with op.operator_context(self.operator):
      self.operator.parameters = self.params
      self.operator.set_step(step)
      step.execute()
    self.mock_interface.add_ok.assert_called_once()
    self.mock_interface.add_skipped.assert_called_once()

  def test_nat_ip_allocation_method_check_auto(self):
    """Test allocation method check branches to auto."""
    step = public_nat_ip_allocation_failed.NatIpAllocationMethodCheck()
    self.mock_get_routers.return_value = [
        MockRouter('test-router',
                   nats=[{
                       'name': 'test-nat-gw'
                   }],
                   ip_allocate_option='AUTO_ONLY')
    ]
    with op.operator_context(self.operator):
      self.operator.parameters = self.params
      self.operator.set_step(step)
      step.execute()
    self.assertIsInstance(
        step.steps[0], public_nat_ip_allocation_failed.NatIpAllocationAutoOnly)

  def test_nat_ip_allocation_method_check_manual(self):
    """Test allocation method check branches to manual."""
    step = public_nat_ip_allocation_failed.NatIpAllocationMethodCheck()
    self.mock_get_routers.return_value = [
        MockRouter('test-router',
                   nats=[{
                       'name': 'test-nat-gw'
                   }],
                   ip_allocate_option='MANUAL_ONLY')
    ]
    with op.operator_context(self.operator):
      self.operator.parameters = self.params
      self.operator.set_step(step)
      step.execute()
    self.assertIsInstance(
        step.steps[0],
        public_nat_ip_allocation_failed.NatIpAllocationManualOnly)

  def test_nat_ip_allocation_auto_only(self):
    """Test NatIpAllocationAutoOnly step."""
    step = public_nat_ip_allocation_failed.NatIpAllocationAutoOnly()
    with op.operator_context(self.operator):
      self.operator.parameters = self.params
      self.operator.set_step(step)
      step.execute()
    self.mock_interface.add_failed.assert_called_once()

  def test_nat_ip_allocation_manual_only_needs_quota(self):
    """Test NatIpAllocationManualOnly when quota increase is needed."""
    step = public_nat_ip_allocation_failed.NatIpAllocationManualOnly()
    self.mock_get_routers.return_value = [
        MockRouter('test-router',
                   nats=[{
                       'name': 'test-nat-gw'
                   }],
                   ip_allocate_option='MANUAL_ONLY')
    ]
    self.mock_nat_router_status.return_value = MockRouterStatus(5, 10)
    nat_ip_info_result = [{
        'natName': 'test-nat-gw',
        'natIpInfoMappings': [{
            'natIp': '1.1.1.1',
            'usage': 'IN_USE'
        }] * 300
    }]
    self.mock_get_nat_ip_info.return_value = MockNatIpInfo(nat_ip_info_result)
    with op.operator_context(self.operator):
      self.operator.parameters = self.params
      self.operator.set_step(step)
      step.execute()
    self.mock_interface.add_ok.assert_called_once()
    self.mock_interface.add_failed.assert_called_once()

  def test_nat_ip_allocation_manual_only_ok(self):
    """Test NatIpAllocationManualOnly when no quota increase is needed."""
    step = public_nat_ip_allocation_failed.NatIpAllocationManualOnly()
    self.mock_get_routers.return_value = [
        MockRouter('test-router',
                   nats=[{
                       'name': 'test-nat-gw'
                   }],
                   ip_allocate_option='MANUAL_ONLY')
    ]
    self.mock_nat_router_status.return_value = MockRouterStatus(5, 10)
    nat_ip_info_result = [{
        'natName': 'test-nat-gw',
        'natIpInfoMappings': [{
            'natIp': '1.1.1.1',
            'usage': 'IN_USE'
        }] * 100
    }]
    self.mock_get_nat_ip_info.return_value = MockNatIpInfo(nat_ip_info_result)
    with op.operator_context(self.operator):
      self.operator.parameters = self.params
      self.operator.set_step(step)
      step.execute()
    # add_ok is called once in all cases, and a second time if ips < 300
    self.assertEqual(self.mock_interface.add_ok.call_count, 2)
    self.mock_interface.add_failed.assert_not_called()

  def test_end_step(self):
    """Test NatIpAllocationFailedEnd step."""
    step = public_nat_ip_allocation_failed.NatIpAllocationFailedEnd()
    with mock.patch('gcpdiag.config.get', return_value=False), \
         mock.patch('gcpdiag.runbook.op.prompt', return_value=op.NO):
      with op.operator_context(self.operator):
        self.operator.parameters = self.params
        self.operator.set_step(step)
        step.execute()
    self.mock_interface.info.assert_called_with(op.END_MESSAGE, 'INFO')

  def test_build_tree(self):
    tree = public_nat_ip_allocation_failed.PublicNatIpAllocationFailed()
    tree.build_tree()
    self.assertIsInstance(
        tree.start, public_nat_ip_allocation_failed.NatIpAllocationFailedStart)

  def test_nat_ip_allocation_manual_only_no_router_status(self):
    step = public_nat_ip_allocation_failed.NatIpAllocationManualOnly()
    self.mock_get_routers.return_value = [
        MockRouter('test-router', nats=[{
            'name': 'test-nat-gw'
        }])
    ]
    self.mock_nat_router_status.return_value = None
    nat_ip_info_result = [{
        'natName': 'test-nat-gw',
        'natIpInfoMappings': [{
            'natIp': '1.1.1.1',
            'usage': 'IN_USE'
        }]
    }]
    self.mock_get_nat_ip_info.return_value = MockNatIpInfo(nat_ip_info_result)
    with op.operator_context(self.operator):
      self.operator.parameters = self.params
      self.operator.set_step(step)
      step.execute()
    self.mock_interface.info.assert_called_once()

  def test_nat_ip_allocation_method_check_get_network_fails(self):
    step = public_nat_ip_allocation_failed.NatIpAllocationMethodCheck()
    mock_response = mock.Mock()
    mock_response.status = 404
    self.mock_get_network.side_effect = googleapiclient.errors.HttpError(
        mock_response, b'not found')
    with op.operator_context(self.operator):
      self.operator.parameters = self.params
      self.operator.set_step(step)
      step.execute()
    self.mock_interface.add_skipped.assert_called_once()

  def test_nat_ip_allocation_method_check_get_routers_fails(self):
    step = public_nat_ip_allocation_failed.NatIpAllocationMethodCheck()
    mock_response = mock.Mock()
    mock_response.status = 404
    self.mock_get_routers.side_effect = googleapiclient.errors.HttpError(
        mock_response, b'not found')
    with op.operator_context(self.operator):
      self.operator.parameters = self.params
      self.operator.set_step(step)
      step.execute()
    self.mock_interface.add_skipped.assert_called_once()

  def test_nat_ip_allocation_method_check_no_router_found(self):
    step = public_nat_ip_allocation_failed.NatIpAllocationMethodCheck()
    self.mock_get_routers.return_value = [
        MockRouter('other-router', nats=[{
            'name': 'test-nat-gw'
        }])
    ]
    with op.operator_context(self.operator):
      self.operator.parameters = self.params
      self.operator.set_step(step)
      step.execute()
    self.mock_interface.add_skipped.assert_called_once()

  def test_end_step_interactive_no(self):
    """Test NatIpAllocationFailedEnd step with interactive mode."""
    step = public_nat_ip_allocation_failed.NatIpAllocationFailedEnd()
    with mock.patch('gcpdiag.config.get', return_value=True), \
         mock.patch('gcpdiag.runbook.op.prompt', return_value=op.NO):
      with op.operator_context(self.operator):
        self.operator.parameters = self.params
        self.operator.set_step(step)
        step.execute()
      self.mock_interface.info.assert_not_called()

  def test_nat_ip_allocation_manual_only_get_network_fails(self):
    step = public_nat_ip_allocation_failed.NatIpAllocationManualOnly()
    mock_response = mock.Mock()
    mock_response.status = 404
    self.mock_get_network.side_effect = googleapiclient.errors.HttpError(
        mock_response, b'not found')
    with op.operator_context(self.operator):
      self.operator.parameters = self.params
      self.operator.set_step(step)
      step.execute()
    self.mock_interface.add_skipped.assert_called_once()

  def test_nat_ip_allocation_manual_only_get_routers_fails(self):
    step = public_nat_ip_allocation_failed.NatIpAllocationManualOnly()
    mock_response = mock.Mock()
    mock_response.status = 404
    self.mock_get_routers.side_effect = googleapiclient.errors.HttpError(
        mock_response, b'not found')
    with op.operator_context(self.operator):
      self.operator.parameters = self.params
      self.operator.set_step(step)
      step.execute()
    self.mock_interface.add_skipped.assert_called_once()

  def test_nat_ip_allocation_manual_only_no_nat_ip_info(self):
    step = public_nat_ip_allocation_failed.NatIpAllocationManualOnly()
    self.mock_get_routers.return_value = [
        MockRouter('test-router', nats=[{
            'name': 'test-nat-gw'
        }])
    ]
    self.mock_nat_router_status.return_value = MockRouterStatus(0, 10)
    self.mock_get_nat_ip_info.return_value = MockNatIpInfo(None)
    with op.operator_context(self.operator):
      self.operator.parameters = self.params
      self.operator.set_step(step)
      step.execute()
    self.assertEqual(self.mock_interface.add_ok.call_count, 1)

  def test_nat_ip_allocation_manual_only_no_routers_list_found(self):
    step = public_nat_ip_allocation_failed.NatIpAllocationManualOnly()
    self.mock_get_routers.return_value = []
    with op.operator_context(self.operator):
      self.operator.parameters = self.params
      self.operator.set_step(step)
      step.execute()
    self.mock_interface.add_skipped.assert_called_once()

  def test_end_step_interactive_yes(self):
    with mock.patch('gcpdiag.config.get', return_value=False), \
         mock.patch('gcpdiag.runbook.op.prompt', return_value=op.YES):
      step = public_nat_ip_allocation_failed.NatIpAllocationFailedEnd()
      with op.operator_context(self.operator):
        self.operator.parameters = self.params
        self.operator.set_step(step)
        step.execute()
      self.mock_interface.info.assert_not_called()


class PublicNatIpAllocationFailedStubDataTest(unittest.TestCase):

  def setUp(self):
    super().setUp()
    self.mock_get_api = self.enterContext(
        mock.patch('gcpdiag.queries.apis.get_api', new=apis_stub.get_api_stub))
    self.mock_monitoring_query = self.enterContext(
        mock.patch('gcpdiag.queries.monitoring.query'))
    self.mock_interface = mock.create_autospec(op.InteractionInterface,
                                               instance=True)
    self.mock_interface.rm = mock.Mock()
    self.operator = op.Operator(self.mock_interface)
    self.operator.run_id = 'test-run'
    self.operator.messages = MockMessage()
    self.params = {
        flags.PROJECT_ID:
            'gcpdiag-nat1-aaaa',
        flags.REGION:
            'europe-west4',
        flags.NAT_GATEWAY_NAME:
            'public-nat-gateway',
        flags.CLOUD_ROUTER_NAME:
            'public-nat-cloud-router',
        flags.NAT_NETWORK:
            'nat-vpc-network',
        'start_time':
            datetime.datetime(2025, 1, 1, 0, 0, 0,
                              tzinfo=datetime.timezone.utc),
        'end_time':
            datetime.datetime(2025, 1, 1, 1, 0, 0,
                              tzinfo=datetime.timezone.utc),
    }

  def test_start_step_success_with_stub_data(self):
    """Test start step with gcpdiag-nat1-aaaa data."""
    step = public_nat_ip_allocation_failed.NatIpAllocationFailedStart()
    with op.operator_context(self.operator):
      self.operator.parameters = self.params
      self.operator.set_step(step)
      step.execute()
    # Based on nat1 data, this step should succeed without skipping
    self.mock_interface.add_skipped.assert_not_called()

  def test_end_step_interactive_yes(self):
    with mock.patch('gcpdiag.config.get', return_value=False), \
         mock.patch('gcpdiag.runbook.op.prompt', return_value=op.YES):
      step = public_nat_ip_allocation_failed.NatIpAllocationFailedEnd()
      with op.operator_context(self.operator):
        self.operator.parameters = self.params
        self.operator.set_step(step)
        step.execute()
      self.mock_interface.info.assert_not_called()
