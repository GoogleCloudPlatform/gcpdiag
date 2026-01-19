# Copyright 2025 Google LLC
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
"""Test class for interconnect/BgpDownFlap."""

import json
import unittest
from datetime import datetime, timezone
from unittest import mock

import googleapiclient.errors

from gcpdiag import config
from gcpdiag.runbook import interconnect, snapshot_test_base
from gcpdiag.runbook.interconnect import bgp_down_flap, flags


class Test(snapshot_test_base.RulesSnapshotTestBase):
  rule_pkg = interconnect
  runbook_name = 'interconnect/bgp-down-flap'
  project_id = 'gcpdiag-interconnect1-aaaa'
  config.init({'auto': True, 'interface': 'cli'}, project_id)

  rule_parameters = [{
      'project_id': 'gcpdiag-interconnect1-aaaa',
      'region': 'us-central1',
      'custom_flag': 'interconnect',
      'attachment_name': 'dummy-attachment11'
  }, {
      'project_id':
          'gcpdiag-interconnect1-aaaa',
      'region':
          'us-east4',
      'custom_flag':
          'interconnect',
      'attachment_name':
          'dummy-attachment1,dummy-attachment2,dummy-attachment3,dummy-attachment4'
  }, {
      'project_id': 'gcpdiag-interconnect1-aaaa',
      'region': 'us-west2',
      'custom_flag': 'interconnect',
      'attachment_name': 'dummy-attachment5,dummy-attachment6'
  }]


class TestBgpDownFlap(unittest.TestCase):
  """Unit tests for bgp_down_flap logic and steps."""

  def setUp(self):
    super().setUp()
    self.project_id = 'test-project'
    self.region = 'us-central1'
    self.project = mock.MagicMock()
    self.project.id = self.project_id

    # Global mocks for queries to prevent 403 errors and real API calls
    self.mock_get_project = mock.patch('gcpdiag.queries.crm.get_project',
                                       return_value=self.project).start()
    self.mock_get_vlan = mock.patch(
        'gcpdiag.queries.interconnect.get_vlan_attachments').start()
    self.mock_get_links = mock.patch(
        'gcpdiag.queries.interconnect.get_links').start()
    self.mock_logs_query = mock.patch(
        'gcpdiag.queries.logs.realtime_query').start()
    self.mock_router_status = mock.patch(
        'gcpdiag.queries.network.nat_router_status').start()

    # Mock the op context for runbook flags and reporting
    self.mock_op_get = mock.patch('gcpdiag.runbook.op.get').start()
    self.mock_op_put = mock.patch('gcpdiag.runbook.op.put').start()
    self.mock_op_add_ok = mock.patch('gcpdiag.runbook.op.add_ok').start()
    self.mock_op_add_failed = mock.patch(
        'gcpdiag.runbook.op.add_failed').start()
    self.mock_op_add_skipped = mock.patch(
        'gcpdiag.runbook.op.add_skipped').start()
    self.mock_op_add_uncertain = mock.patch(
        'gcpdiag.runbook.op.add_uncertain').start()
    self.mock_op_prep_msg = mock.patch('gcpdiag.runbook.op.prep_msg').start()
    self.mock_op_info = mock.patch('gcpdiag.runbook.op.info').start()

    self.op_flags = {
        flags.PROJECT_ID: self.project_id,
        flags.REGION: self.region,
        flags.ATTACHMENT_NAME: 'vlan1',
        flags.ATTACHMENT_LIST: 'vlan1',
        flags.ERROR_LIST: '',
        flags.START_TIME: datetime(2025, 1, 1, tzinfo=timezone.utc),
        flags.END_TIME: datetime(2025, 1, 2, tzinfo=timezone.utc),
        flags.BGP_FLAP_LIST: '{}'
    }
    self.mock_op_get.side_effect = self.op_flags.get
    self.mock_operator = mock.MagicMock(parameters={})

  def tearDown(self):
    super().tearDown()
    mock.patch.stopall()

  def _create_vlan_mock(self, name='vlan1', ipv4='2.2.2.2'):
    """Helper to create a vlan mock with consistent attributes."""
    v = mock.MagicMock()
    v.name = name
    v.region = self.region
    v.ipv4address = ipv4  # Logic compares item['ipAddress'] to this field
    v.remoteip = ipv4
    v.interconnect = 'ic1'
    v.router = 'r1'
    return v

  def test_get_time_delta(self):
    result = bgp_down_flap.get_time_delta('2025-01-01T10:00:00Z',
                                          '2025-01-01T10:00:05.5Z')
    self.assertEqual(result, '5.5')

  def test_local_realtime_query(self):
    bgp_down_flap.local_realtime_query('t1', 't2', 'filter')
    self.mock_logs_query.assert_called()

  def test_start_step_handles_api_failure(self):
    self.mock_get_vlan.side_effect = googleapiclient.errors.HttpError(
        mock.MagicMock(status=403), b'Forbidden')
    step = bgp_down_flap.BgpDownFlapStart()
    with bgp_down_flap.op.operator_context(self.mock_operator):
      step.execute()
    self.mock_op_add_skipped.assert_called()

  def test_check_bgp_down_detects_failure(self):
    test_ip = '1.1.1.1'
    project_id = 'test-project'
    attachment_name = 'attachment1'
    region = 'us-central1'

    self.mock_op_get.side_effect = lambda key, default=None: {
        flags.PROJECT_ID: project_id,
        flags.REGION: region,
        flags.ATTACHMENT_LIST: attachment_name
    }.get(key, default)

    project = mock.MagicMock()
    project.id = project_id
    self.mock_get_project.return_value = project

    vlan = mock.MagicMock()
    vlan.name = attachment_name
    vlan.region = region
    vlan.ipv4address = test_ip
    vlan.router = 'router1'
    vlan.interconnect = 'interconnect1'
    self.mock_get_vlan.return_value = [vlan]

    mock_status = mock.MagicMock()
    mock_status.bgp_peer_status = [{'ipAddress': test_ip, 'state': 'Active'}]
    self.mock_router_status.return_value = mock_status

    step = bgp_down_flap.CheckBgpDown()
    with bgp_down_flap.op.operator_context(self.mock_operator):
      step.execute()

    self.mock_op_add_failed.assert_called()

  def test_check_bgp_down_ok(self):
    test_ip = '2.2.2.2'
    vlan = self._create_vlan_mock(ipv4=test_ip)
    self.mock_get_vlan.return_value = [vlan]
    router_status = mock.MagicMock()
    router_status.bgp_peer_status = [{
        'ipAddress': test_ip,
        'state': 'Established'
    }]
    self.mock_router_status.return_value = router_status
    step = bgp_down_flap.CheckBgpDown()
    with bgp_down_flap.op.operator_context(self.mock_operator):
      step.execute()
    self.mock_op_add_ok.assert_called()

  def test_start_step_ok(self):
    vlan = self._create_vlan_mock(name='vlan1')
    self.mock_get_vlan.return_value = [vlan]
    step = bgp_down_flap.BgpDownFlapStart()
    with bgp_down_flap.op.operator_context(self.mock_operator):
      step.execute()
    self.mock_op_add_ok.assert_called()

  def test_start_step_attachment_not_found(self):
    self.op_flags[flags.ATTACHMENT_NAME] = 'non-existent-vlan'
    vlan = self._create_vlan_mock(name='vlan1')
    self.mock_get_vlan.return_value = [vlan]
    step = bgp_down_flap.BgpDownFlapStart()
    with bgp_down_flap.op.operator_context(self.mock_operator):
      step.execute()
    self.mock_op_add_skipped.assert_called()

  def test_check_ic_maintenance_skipped_no_errors(self):
    self.op_flags[flags.ERROR_LIST] = ''
    step = bgp_down_flap.CheckInterconnectMaintenance()
    with bgp_down_flap.op.operator_context(self.mock_operator):
      step.execute()
    self.mock_op_add_skipped.assert_called()

  def test_check_ic_maintenance_skipped_no_links(self):
    self.op_flags[flags.ERROR_LIST] = 'ic1'
    self.mock_get_links.return_value = []
    step = bgp_down_flap.CheckInterconnectMaintenance()
    with bgp_down_flap.op.operator_context(self.mock_operator):
      step.execute()
    self.mock_op_add_skipped.assert_called()

  def test_check_ic_maintenance_ok(self):
    self.op_flags[flags.ERROR_LIST] = 'ic1'
    ic_link = mock.MagicMock()
    ic_link.name = 'ic1'
    ic_link.under_maintenance = True
    self.mock_get_links.return_value = [ic_link]
    step = bgp_down_flap.CheckInterconnectMaintenance()
    with bgp_down_flap.op.operator_context(self.mock_operator):
      step.execute()
    self.mock_op_add_ok.assert_called()

  def test_check_ic_maintenance_unexplained_down(self):
    self.op_flags[flags.ERROR_LIST] = 'ic1'
    ic_link = mock.MagicMock()
    ic_link.name = 'ic1'
    ic_link.under_maintenance = False
    self.mock_get_links.return_value = [ic_link]

    step = bgp_down_flap.CheckInterconnectMaintenance()
    with bgp_down_flap.op.operator_context(self.mock_operator):
      step.execute()
    self.mock_op_add_failed.assert_called()

  def test_check_cr_maintenance_detects_unexplained_flap(self):
    flap_data = {
        'r1_id--2.2.2.2': {
            'uncertain_flag':
                'True',
            'router_id':
                'r1_id',
            'local_ip':
                '1.1.1.1',
            'remote_ip':
                '2.2.2.2',
            'router_name':
                'r1',
            'attachment_name':
                'vlan1',
            'project_id':
                self.project_id,
            'events': [[
                'went down,2025-01-01T12:00:00Z,came up,2025-01-01T12:01:00Z'
            ]],
        }
    }
    self.op_flags[flags.BGP_FLAP_LIST] = json.dumps(flap_data)
    self.mock_logs_query.return_value = []

    step = bgp_down_flap.CheckCloudRouterMaintenance()
    with bgp_down_flap.op.operator_context(self.mock_operator):
      step.execute()
    self.mock_op_add_failed.assert_called()

  def test_check_cr_maintenance_skipped_no_uncertain_flaps(self):
    self.op_flags[flags.BGP_FLAP_LIST] = '{}'
    step = bgp_down_flap.CheckCloudRouterMaintenance()
    with bgp_down_flap.op.operator_context(self.mock_operator):
      step.execute()
    self.mock_op_add_skipped.assert_called()

  def test_check_cr_maintenance_ok(self):
    flap_data = {
        'r1_id--2.2.2.2': {
            'uncertain_flag':
                'True',
            'router_id':
                'r1_id',
            'local_ip':
                '1.1.1.1',
            'remote_ip':
                '2.2.2.2',
            'router_name':
                'r1',
            'attachment_name':
                'vlan1',
            'project_id':
                self.project_id,
            'events': [[
                'went down,2025-01-01T12:00:00Z,came up,2025-01-01T12:01:00Z',
                '60.0', 'Uncertain'
            ]],
        }
    }
    self.op_flags[flags.BGP_FLAP_LIST] = json.dumps(flap_data)
    self.mock_logs_query.return_value = [{
        'textPayload': 'Maintenance of router task',
        'timestamp': '2025-01-01T12:00:30Z',
        'resource': {
            'labels': {
                'router_id': 'r1_id',
                'region': self.region
            }
        },
    }]
    step = bgp_down_flap.CheckCloudRouterMaintenance()
    with bgp_down_flap.op.operator_context(self.mock_operator):
      step.execute()
    self.mock_op_add_ok.assert_called()

  def test_check_bgp_flap_logic(self):
    vlan = self._create_vlan_mock(ipv4='1.1.1.1')
    vlan.remoteip = '2.2.2.2'
    self.mock_get_vlan.return_value = [vlan]

    self.mock_logs_query.return_value = [
        {
            'textPayload': 'BGP Event: BGP peering with 2.2.2.2 went down',
            'timestamp': '2025-01-01T12:00:00Z',
            'resource': {
                'labels': {
                    'router_id': 'r1_id',
                    'region': self.region
                }
            },
        },
        {
            'textPayload': 'BGP Event: BGP peering with 2.2.2.2 came up',
            'timestamp': '2025-01-01T12:05:00Z',
            'resource': {
                'labels': {
                    'router_id': 'r1_id',
                    'region': self.region
                }
            },
        },
    ]
    step = bgp_down_flap.CheckBgpFlap()
    with bgp_down_flap.op.operator_context(self.mock_operator):
      step.execute()
    self.mock_op_add_failed.assert_called()

  def test_check_bgp_flap_skipped_on_api_error(self):
    self.mock_get_vlan.side_effect = googleapiclient.errors.HttpError(
        mock.MagicMock(status=403), b'Forbidden')
    step = bgp_down_flap.CheckBgpFlap()
    with bgp_down_flap.op.operator_context(self.mock_operator):
      step.execute()
    self.mock_op_add_skipped.assert_called_once()

  def test_check_bgp_flap_ok_no_flaps(self):
    vlan = self._create_vlan_mock(ipv4='1.1.1.1')
    vlan.remoteip = '2.2.2.2'
    self.mock_get_vlan.return_value = [vlan]
    self.mock_logs_query.return_value = []
    step = bgp_down_flap.CheckBgpFlap()
    with bgp_down_flap.op.operator_context(self.mock_operator):
      step.execute()
    self.mock_op_add_ok.assert_called()

  def test_check_bgp_flap_uncertain(self):
    vlan = self._create_vlan_mock(ipv4='1.1.1.1')
    vlan.remoteip = '2.2.2.2'
    self.mock_get_vlan.return_value = [vlan]
    self.mock_logs_query.return_value = [
        {
            'textPayload': 'BGP Event: BGP peering with 2.2.2.2 went down',
            'timestamp': '2025-01-01T12:00:00Z',
            'resource': {
                'labels': {
                    'router_id': 'r1_id',
                    'region': self.region
                }
            },
        },
        {
            'textPayload': 'BGP Event: BGP peering with 2.2.2.2 came up',
            'timestamp': '2025-01-01T12:01:00Z',
            'resource': {
                'labels': {
                    'router_id': 'r1_id',
                    'region': self.region
                }
            },
        },
    ]
    step = bgp_down_flap.CheckBgpFlap()
    with bgp_down_flap.op.operator_context(self.mock_operator):
      step.execute()
    self.mock_op_add_uncertain.assert_called()

  def test_check_bgp_flap_log_reversal(self):
    vlan = self._create_vlan_mock(ipv4='1.1.1.1')
    vlan.remoteip = '2.2.2.2'
    self.mock_get_vlan.return_value = [vlan]
    self.mock_logs_query.return_value = [
        {
            'textPayload': 'BGP Event: BGP peering with 2.2.2.2 came up',
            'timestamp': '2025-01-01T12:01:00Z',
            'resource': {
                'labels': {
                    'router_id': 'r1_id',
                    'region': self.region
                }
            },
        },
        {
            'textPayload': 'BGP Event: BGP peering with 2.2.2.2 went down',
            'timestamp': '2025-01-01T12:00:00Z',
            'resource': {
                'labels': {
                    'router_id': 'r1_id',
                    'region': self.region
                }
            },
        },
    ]
    step = bgp_down_flap.CheckBgpFlap()
    with bgp_down_flap.op.operator_context(self.mock_operator):
      step.execute()
    self.mock_op_add_uncertain.assert_called()

  def test_end_step(self):
    step = bgp_down_flap.BgpDownFlapEnd()
    with bgp_down_flap.op.operator_context(self.mock_operator):
      step.execute()
    self.mock_op_info.assert_called()


if __name__ == '__main__':
  unittest.main()
