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
"""Test class for gke/NodeUnavailability"""

import unittest
from unittest import mock

from gcpdiag import config
from gcpdiag.queries import apis_stub
from gcpdiag.runbook import gke, op, snapshot_test_base
from gcpdiag.runbook.gke import flags, node_unavailability


class Test(snapshot_test_base.RulesSnapshotTestBase):
  rule_pkg = gke
  runbook_name = 'gke/node-unavailability'
  config.init({'auto': True, 'interface': 'cli'})

  rule_parameters = [{
      'project_id': 'gcpdiag-gke-cluster-autoscaler-rrrr',
      'gke_cluster_name': 'gcp-cluster',
      'node': 'gke-gcp-cluster-default-pool-82e0c046-8m8b',
      'location': 'europe-west10-a'
  }]


class MockMessage:
  """Mock messages for testing."""

  def get_msg(self, key, **kwargs):
    del kwargs
    return f'{key}'


class TestNodeUnavailability(unittest.TestCase):
  """Unit tests for NodeUnavailability runbook."""

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
    node_unavailability.LOG_PREEMPTED = None
    node_unavailability.LOG_MIGRATED = None
    node_unavailability.LOG_DELETED = None
    self.mock_op_get = self.enterContext(mock.patch('gcpdiag.runbook.op.get'))
    self.mock_op_add_ok = self.enterContext(
        mock.patch('gcpdiag.runbook.op.add_ok'))
    self.mock_op_add_failed = self.enterContext(
        mock.patch('gcpdiag.runbook.op.add_failed'))
    self.mock_op_add_skipped = self.enterContext(
        mock.patch('gcpdiag.runbook.op.add_skipped'))
    self.mock_op_prompt = self.enterContext(
        mock.patch('gcpdiag.runbook.op.prompt'))
    self.mock_op_info = self.enterContext(mock.patch('gcpdiag.runbook.op.info'))
    self.mock_op_prep_msg = self.enterContext(
        mock.patch('gcpdiag.runbook.op.prep_msg'))
    self.mock_crm_get_project = self.enterContext(
        mock.patch('gcpdiag.queries.crm.get_project'))
    self.mock_gke_get_clusters = self.enterContext(
        mock.patch('gcpdiag.queries.gke.get_clusters'))

    self.params = {
        flags.PROJECT_ID: 'test-project',
        flags.LOCATION: 'us-central1-a',
        flags.NODE: 'test-node',
        flags.GKE_CLUSTER_NAME: 'test-cluster',
        flags.START_TIME: '2025-01-01T00:00:00Z',
        flags.END_TIME: '2025-01-01T01:00:00Z',
    }
    self.mock_op_get.side_effect = lambda key, default=None: self.params.get(
        key, default)

    self.mock_project = mock.Mock()
    self.mock_project.full_path = 'projects/test-project'
    self.mock_crm_get_project.return_value = self.mock_project

    mock_interface = mock.Mock()
    operator = op.Operator(mock_interface)
    operator.set_parameters(self.params)
    self.enterContext(op.operator_context(operator))

  @mock.patch('gcpdiag.queries.logs.realtime_query')
  def test_local_realtime_query(self, mock_realtime_query):
    """Test local_realtime_query (Lines 26-32)"""
    node_unavailability.local_realtime_query('test-filter')
    mock_realtime_query.assert_called_once()

  def test_legacy_parameter_handler(self):
    """Test legacy_parameter_handler (Lines 81-82)"""
    runbook_instance = node_unavailability.NodeUnavailability()
    params = {flags.NAME: 'cluster-name'}
    runbook_instance.legacy_parameter_handler(params)
    self.assertEqual(params[flags.GKE_CLUSTER_NAME], 'cluster-name')
    self.assertNotIn(flags.NAME, params)

  def test_build_tree(self):
    """Test build_tree (Lines 86-97)"""
    runbook_instance = node_unavailability.NodeUnavailability()
    runbook_instance.build_tree()
    self.assertIsInstance(runbook_instance.start,
                          node_unavailability.NodeUnavailabilityStart)

  def test_node_unavailability_start_no_clusters(self):
    """Test NodeUnavailabilityStart when no clusters are found (Lines 118-121)"""
    self.mock_gke_get_clusters.return_value = []
    step = node_unavailability.NodeUnavailabilityStart()
    step.execute()
    self.mock_op_add_skipped.assert_called_once_with(mock.ANY, reason=mock.ANY)

  @mock.patch('gcpdiag.runbook.gke.node_unavailability.local_realtime_query')
  def test_node_unavailability_start_no_logs(self, mock_local_query):
    """Test NodeUnavailabilityStart when no unavailability logs are found (Lines 153-162)"""
    self.mock_gke_get_clusters.return_value = ['cluster1']
    mock_local_query.return_value = []  # Return empty for all log queries
    step = node_unavailability.NodeUnavailabilityStart()
    step.execute()
    self.mock_op_add_skipped.assert_called_once()

  def test_live_migration_failed(self):
    """Test LiveMigration step when logs are present (Lines 177-179)"""
    node_unavailability.LOG_MIGRATED = ['log-entry']
    step = node_unavailability.LiveMigration()
    step.execute()
    self.mock_op_add_failed.assert_called_once()

  def test_live_migration_ok(self):
    """Test LiveMigration step when no logs are present (Line 181)"""
    node_unavailability.LOG_MIGRATED = []
    step = node_unavailability.LiveMigration()
    step.execute()
    self.mock_op_add_ok.assert_called_once()

  def test_preemption_failed(self):
    """Test PreemptionCondition step when logs are present (Lines 196-198)"""
    node_unavailability.LOG_PREEMPTED = ['log-entry']
    step = node_unavailability.PreemptionCondition()
    step.execute()
    self.mock_op_add_failed.assert_called_once()

  def test_preemption_ok(self):
    """Test PreemptionCondition step when no logs are present (Line 200)"""
    node_unavailability.LOG_PREEMPTED = []
    step = node_unavailability.PreemptionCondition()
    step.execute()
    self.mock_op_add_ok.assert_called_once()

  @mock.patch('gcpdiag.runbook.gke.node_unavailability.local_realtime_query')
  def test_autoscaler_removal_failed(self, mock_local_query):
    """Test NodeRemovedByAutoscaler when logs exist (Lines 229-231)"""
    mock_local_query.return_value = ['scale-down-log']
    node_unavailability.LOG_DELETED = ['delete-log']
    step = node_unavailability.NodeRemovedByAutoscaler()
    step.execute()
    self.mock_op_add_failed.assert_called_once()

  @mock.patch('gcpdiag.runbook.gke.node_unavailability.local_realtime_query')
  def test_autoscaler_removal_ok(self, mock_local_query):
    """Test NodeRemovedByAutoscaler when no scale-down logs exist (Line 234)"""
    mock_local_query.return_value = []
    step = node_unavailability.NodeRemovedByAutoscaler()
    step.execute()
    self.mock_op_add_ok.assert_called_once()

  @mock.patch('gcpdiag.runbook.gke.node_unavailability.local_realtime_query')
  def test_node_pool_upgrade_failed(self, mock_local_query):
    """Test NodePoolUpgrade when logs exist (Lines 265-267)"""
    mock_local_query.return_value = ['upgrade-log']
    node_unavailability.LOG_DELETED = ['delete-log']
    step = node_unavailability.NodePoolUpgrade()
    step.execute()
    self.mock_op_add_failed.assert_called_once()

  @mock.patch('gcpdiag.runbook.gke.node_unavailability.local_realtime_query')
  def test_node_pool_upgrade_ok(self, mock_local_query):
    """Test NodePoolUpgrade when no upgrade logs exist (Line 270)"""
    mock_local_query.return_value = []
    step = node_unavailability.NodePoolUpgrade()
    step.execute()
    self.mock_op_add_ok.assert_called_once()

  def test_node_unavailability_end_not_satisfied(self):
    """Test NodeUnavailabilityEnd when user is not satisfied (Lines 291-293)"""
    self.mock_op_prompt.return_value = op.NO
    step = node_unavailability.NodeUnavailabilityEnd()
    step.execute()
    self.mock_op_info.assert_called_once()
