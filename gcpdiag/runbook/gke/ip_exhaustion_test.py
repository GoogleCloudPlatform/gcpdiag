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
"""Test class for gke/IpExhaustionIssues."""

import unittest
from unittest import mock

from gcpdiag import config
from gcpdiag.queries import apis_stub
from gcpdiag.runbook import gke, op, snapshot_test_base
from gcpdiag.runbook.gke import flags, ip_exhaustion
from gcpdiag.utils import GcpApiError


class MockMessage:
  """Mock messages for testing."""

  def get_msg(self, key, **kwargs):
    del kwargs
    return f'{key}'


class Test(snapshot_test_base.RulesSnapshotTestBase):
  rule_pkg = gke
  runbook_name = 'gke/ip-exhaustion'
  config.init({'auto': True, 'interface': 'cli'})

  rule_parameters = [{
      'project_id': 'gcpdiag-gke3-gggg',
      'gke_cluster_name': 'cluster-1',
      'location': 'us-central1-c',
      'start_time': '2024-06-30T01:00:00Z',
      'end_time': '2024-06-30T23:00:00Z'
  }]


class TestIpExhaustionUnit(unittest.TestCase):
  """Unit tests covering the diagnostic tree and individual steps."""

  def setUp(self):
    super().setUp()
    self.enterContext(
        mock.patch('gcpdiag.queries.apis.get_api', new=apis_stub.get_api_stub))
    self.mock_get_user_email = self.enterContext(
        mock.patch('gcpdiag.queries.apis.get_user_email'))
    self.mock_is_enabled = self.enterContext(
        mock.patch('gcpdiag.queries.apis.is_enabled'))
    self.mock_is_enabled.return_value = True
    self.mock_get_user_email.return_value = 'test@example.com'

    self.mock_interface = mock.create_autospec(op.InteractionInterface,
                                               instance=True)
    self.mock_interface.rm = mock.Mock()
    self.operator = op.Operator(self.mock_interface)
    self.operator.run_id = 'test-run'
    self.operator.messages = MockMessage()
    self.project_id = 'test-project'
    self.cluster_name = 'test-cluster'
    self.location = 'us-central1-a'
    self.enterContext(
        mock.patch('gcpdiag.runbook.op.get_context', autospec=True))
    self.enterContext(
        mock.patch(
            'gcpdiag.runbook.op.prep_msg',
            side_effect=lambda x, **y: x,
            autospec=True,
        ))
    self.enterContext(mock.patch('gcpdiag.runbook.op.info', autospec=True))

  @mock.patch('gcpdiag.runbook.op.get')
  @mock.patch('gcpdiag.queries.logs.realtime_query')
  def test_local_realtime_query(self, mock_query, mock_op_get):
    """Covers lines 26-30: Verifies the log query helper correctly handles parameters."""
    mock_op_get.side_effect = lambda k, default=None: {
        flags.PROJECT_ID: self.project_id,
        flags.START_TIME: '2024-06-30T01:00:00Z',
        flags.END_TIME: '2024-06-30T23:00:00Z'
    }.get(k, default)

    ip_exhaustion.local_realtime_query('test-filter')
    mock_query.assert_called_once_with(project_id=self.project_id,
                                       start_time='2024-06-30T01:00:00Z',
                                       end_time='2024-06-30T23:00:00Z',
                                       filter_str='test-filter')

  def test_legacy_parameter_handler(self):
    """Covers lines 89-90: Verifies handling of deprecated 'name' parameter."""
    tree = ip_exhaustion.IpExhaustion()
    params = {flags.NAME: 'old-name-param'}
    tree.legacy_parameter_handler(params)
    self.assertEqual(params[flags.GKE_CLUSTER_NAME], 'old-name-param')
    self.assertNotIn(flags.NAME, params)

  @mock.patch('gcpdiag.runbook.op.get')
  @mock.patch('gcpdiag.queries.crm.get_project')
  @mock.patch('gcpdiag.queries.gke.get_cluster')
  @mock.patch('gcpdiag.runbook.op.add_skipped')
  def test_start_step_cluster_not_found(self, mock_skip, mock_get_cluster,
                                        unused_mock_get_project, mock_op_get):
    """Covers lines 116-122: Verifies skipping when GKE cluster is not found."""
    mock_op_get.side_effect = lambda k, default=None: {
        flags.PROJECT_ID: self.project_id,
        flags.GKE_CLUSTER_NAME: self.cluster_name,
        flags.LOCATION: self.location
    }.get(k, default)
    # Simulate API error for non-existent cluster
    mock_response = mock.Mock()
    mock_response.status = 404
    mock_response.content = b'{"error": "cluster not found"}'
    mock_get_cluster.side_effect = GcpApiError(mock_response)

    step = ip_exhaustion.IpExhaustionStart()
    step.execute()
    mock_skip.assert_called_once()
    self.assertIn('does not exist', mock_skip.call_args[1]['reason'])

  @mock.patch('gcpdiag.runbook.op.get')
  @mock.patch('gcpdiag.queries.gke.get_cluster')
  @mock.patch('gcpdiag.runbook.gke.ip_exhaustion.local_realtime_query')
  @mock.patch('gcpdiag.runbook.op.add_failed')
  def test_node_exhaustion_detected(self, mock_failed, mock_query,
                                    unused_mock_get_cluster, mock_op_get):
    """Covers lines 147-187: Verifies failure report when Node IP exhaustion logs found."""
    mock_op_get.side_effect = lambda k, default=None: {
        flags.PROJECT_ID: self.project_id,
        flags.GKE_CLUSTER_NAME: self.cluster_name,
        flags.LOCATION: self.location
    }.get(k, default)
    mock_query.return_value = ['IP_SPACE_EXHAUSTED log entry']

    step = ip_exhaustion.NodeIpRangeExhaustion()
    step.execute()
    mock_failed.assert_called_once()

  @mock.patch('gcpdiag.runbook.op.get')
  @mock.patch('gcpdiag.queries.gke.get_cluster')
  @mock.patch('gcpdiag.runbook.gke.ip_exhaustion.local_realtime_query')
  @mock.patch('gcpdiag.runbook.op.add_failed')
  def test_pod_exhaustion_autopilot_detected(self, mock_failed, mock_query,
                                             mock_get_cluster, mock_op_get):
    """Covers lines 204-273: Verifies Autopilot-specific failure logic for Pod IP exhaustion."""
    mock_op_get.side_effect = lambda k, default=None: {
        flags.PROJECT_ID: self.project_id,
        flags.GKE_CLUSTER_NAME: self.cluster_name,
        flags.LOCATION: self.location
    }.get(k, default)
    mock_query.return_value = ['found pod exhaustion log']
    cluster = mock_get_cluster.return_value
    cluster.is_autopilot = True
    cluster.get_nodepool_config = [{'networkConfig': {'podRange': 'range-1'}}]

    step = ip_exhaustion.PodIpRangeExhaustion()
    step.execute()
    mock_failed.assert_called_once()

  @mock.patch('gcpdiag.config.get')
  @mock.patch('gcpdiag.runbook.op.get')
  @mock.patch('gcpdiag.runbook.op.prompt')
  @mock.patch('gcpdiag.runbook.op.info')
  def test_end_step_resolution_confirmation(self, mock_info, mock_prompt,
                                            mock_op_get, mock_config_get):
    """Covers lines 290-298: Verifies final prompt logic in non-interactive mode."""
    mock_config_get.return_value = False  # Force prompt trigger
    mock_prompt.return_value = 'NO'
    mock_op_get.return_value = self.cluster_name

    with mock.patch('gcpdiag.runbook.op.NO', 'NO'):
      step = ip_exhaustion.IpExhaustionEnd()
      step.execute()
      mock_prompt.assert_called_once()
      mock_info.assert_called_with(message=mock.ANY)

  def test_build_tree(self):
    """Covers lines 96-107: Verifies the diagnostic tree structure and step relationships."""
    tree = ip_exhaustion.IpExhaustion()
    tree.build_tree()
    self.assertIsNotNone(tree.start)
    self.assertIsInstance(tree.start, ip_exhaustion.IpExhaustionStart)
    self.assertEqual(tree.start.doc_file_name, 'ip-exhaustion-start')
    self.assertEqual(len(tree.start.steps), 2)
    self.assertIsInstance(tree.start.steps[0],
                          ip_exhaustion.NodeIpRangeExhaustion)
    self.assertIsInstance(tree.start.steps[1], ip_exhaustion.IpExhaustionEnd)
    self.assertIsInstance(tree.start.steps[0].steps[0],
                          ip_exhaustion.PodIpRangeExhaustion)

  @mock.patch('gcpdiag.runbook.op.get')
  @mock.patch('gcpdiag.queries.crm.get_project')
  @mock.patch('gcpdiag.queries.gke.get_cluster')
  @mock.patch('gcpdiag.runbook.op.add_ok')
  def test_start_step_cluster_found(self, mock_ok, mock_get_cluster,
                                    unused_mock_get_project, mock_op_get):
    """Covers line 128: Verifies success path when the GKE cluster exists."""
    mock_op_get.side_effect = lambda k, default=None: {
        flags.PROJECT_ID: self.project_id,
        flags.GKE_CLUSTER_NAME: self.cluster_name,
        flags.LOCATION: self.location
    }.get(k, default)
    mock_get_cluster.return_value.name = self.cluster_name

    step = ip_exhaustion.IpExhaustionStart()
    step.execute()
    # Confirms op.add_ok is called (line 128)
    mock_ok.assert_called_once()
    self.assertIn('found', mock_ok.call_args[1]['reason'])

  @mock.patch('gcpdiag.runbook.op.get')
  @mock.patch('gcpdiag.queries.gke.get_cluster')
  @mock.patch('gcpdiag.runbook.gke.ip_exhaustion.local_realtime_query')
  @mock.patch('gcpdiag.runbook.op.add_ok')
  def test_node_exhaustion_not_found(self, mock_ok, mock_query,
                                     unused_mock_get_cluster, mock_op_get):
    """Covers line 187: Verifies OK status when no Node IP exhaustion logs are found."""
    mock_op_get.side_effect = lambda k, default=None: {
        flags.PROJECT_ID: self.project_id,
        flags.GKE_CLUSTER_NAME: self.cluster_name,
        flags.LOCATION: self.location
    }.get(k, default)
    mock_query.return_value = []  # Simulate no exhaustion logs

    step = ip_exhaustion.NodeIpRangeExhaustion()
    step.execute()
    # Confirms op.add_ok is called (line 187)
    mock_ok.assert_called_once()

  @mock.patch('gcpdiag.runbook.op.get')
  @mock.patch('gcpdiag.queries.gke.get_cluster')
  @mock.patch('gcpdiag.runbook.gke.ip_exhaustion.local_realtime_query')
  @mock.patch('gcpdiag.runbook.op.add_failed')
  @mock.patch('gcpdiag.runbook.op.info')
  def test_pod_exhaustion_standard_cluster_detected(self, mock_info,
                                                    mock_failed, mock_query,
                                                    mock_get_cluster,
                                                    mock_op_get):
    """Covers lines 243, 266-273: Verifies failure logic for Standard GKE clusters."""
    mock_op_get.side_effect = lambda k, default=None: {
        flags.PROJECT_ID: self.project_id,
        flags.GKE_CLUSTER_NAME: self.cluster_name,
        flags.LOCATION: self.location
    }.get(k, default)
    mock_query.return_value = ['IP_SPACE_EXHAUSTED']
    cluster = mock_get_cluster.return_value
    cluster.is_autopilot = False
    cluster.get_nodepool_config = [{'networkConfig': {'podRange': 'range-1'}}]
    step = ip_exhaustion.PodIpRangeExhaustion()
    step.execute()
    mock_failed.assert_called_once()
    mock_info.assert_any_call('Cluster is a Standard cluster')

  @mock.patch('gcpdiag.runbook.op.get')
  @mock.patch('gcpdiag.queries.gke.get_cluster')
  @mock.patch('gcpdiag.runbook.gke.ip_exhaustion.local_realtime_query')
  @mock.patch('gcpdiag.runbook.op.add_ok')
  def test_pod_exhaustion_not_found(self, mock_ok, mock_query, mock_get_cluster,
                                    mock_op_get):
    """Verifies OK when no Pod IP exhaustion logs found."""
    mock_op_get.side_effect = lambda k, default=None: {
        flags.PROJECT_ID: self.project_id,
        flags.GKE_CLUSTER_NAME: self.cluster_name,
        flags.LOCATION: self.location
    }.get(k, default)
    mock_query.return_value = []
    cluster = mock_get_cluster.return_value
    cluster.get_nodepool_config = [{'networkConfig': {'podRange': 'range-1'}}]
    step = ip_exhaustion.PodIpRangeExhaustion()
    step.execute()
    mock_ok.assert_called_once()
