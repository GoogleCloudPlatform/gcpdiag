# Copyright 2024 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Test class for gke/NodeBootstrapping."""

import collections
import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import ANY, MagicMock, patch

from googleapiclient.errors import HttpError

from gcpdiag import config
from gcpdiag.queries import crm_stub, gce_stub, gke_stub, iam_stub, logs_stub
from gcpdiag.runbook import gke, op, snapshot_test_base
from gcpdiag.runbook.gke import flags, node_bootstrapping

TEST_TIME = datetime(2026, 1, 8, 12, 0, 0, tzinfo=timezone.utc)


class MockDatetime(datetime):

  @classmethod
  def now(cls, tz=None):
    if tz:
      return TEST_TIME.astimezone(tz)
    return TEST_TIME


class Test(snapshot_test_base.RulesSnapshotTestBase):
  rule_pkg = gke
  runbook_name = 'gke/node-bootstrapping'
  config.init({'auto': True, 'interface': 'cli'})

  rule_parameters = [{
      'project_id': 'gcpdiag-gke1-aaaa',
      'nodepool': 'gke-gke1-default-pool-671518f6',
      'location': 'europe-west4-a',
      'gke_cluster_name': 'gke-cluster-name',
  }]


class TestNodeBootstrappingCoverage(unittest.TestCase):
  """Comprehensive test suite for node_bootstrapping.py to reach 100% coverage.

  Follows Arrange-Act-Assert and Behavior-Driven Testing patterns.
  """

  def setUp(self):
    super().setUp()
    patcher = patch('gcpdiag.runbook.gke.node_bootstrapping.datetime',
                    MockDatetime)
    patcher.start()
    self.addCleanup(patcher.stop)
    self.op_add_ok = patch('gcpdiag.runbook.op.add_ok').start()
    self.op_add_failed = patch('gcpdiag.runbook.op.add_failed').start()
    self.op_add_skipped = patch('gcpdiag.runbook.op.add_skipped').start()
    self.mock_gke = patch('gcpdiag.runbook.gke.node_bootstrapping.gke',
                          gke_stub).start()
    self.mock_gce = patch('gcpdiag.runbook.gke.node_bootstrapping.gce',
                          gce_stub).start()
    self.mock_crm = patch('gcpdiag.runbook.gke.node_bootstrapping.crm',
                          crm_stub).start()
    self.mock_iam = patch('gcpdiag.runbook.gke.node_bootstrapping.iam',
                          iam_stub).start()
    self.mock_logs_module = patch('gcpdiag.runbook.gke.node_bootstrapping.logs',
                                  logs_stub).start()
    self.mock_realtime_query = patch('gcpdiag.queries.logs_stub.realtime_query',
                                     create=True).start()
    self.mock_get_clusters = patch('gcpdiag.queries.gke_stub.get_clusters',
                                   create=True).start()
    self.mock_get_instance = patch('gcpdiag.queries.gce_stub.get_instance',
                                   create=True).start()
    self.mock_get_project = patch('gcpdiag.queries.crm_stub.get_project',
                                  create=True).start()
    self.mock_get_project_policy = patch(
        'gcpdiag.queries.iam_stub.get_project_policy', create=True).start()

    self.params = {
        flags.PROJECT_ID: 'test-project',
        flags.LOCATION: 'us-central1-a',
        flags.NODE: 'test-node',
        flags.GKE_CLUSTER_NAME: 'test-cluster',
        flags.START_TIME: TEST_TIME - timedelta(hours=1),
        flags.END_TIME: TEST_TIME,
        flags.NODEPOOL: 'test-pool',
    }
    self.mock_op_parent = MagicMock()
    self.mock_op_parent.parameters = self.params

    self.addCleanup(patch.stopall)

  def create_mock_vm(self, is_gke=True, serial_enabled=True, running=True):
    vm = MagicMock()
    vm.is_gke_node.return_value = is_gke
    vm.is_serial_port_logging_enabled.return_value = serial_enabled
    vm.is_running = running
    vm.id = '12345'
    vm.service_account = 'test-sa@project.iam.gserviceaccount.com'
    vm.creation_timestamp = TEST_TIME - timedelta(minutes=15)
    return vm

  def test_start_no_clusters_named(self):
    """Cluster name provided but not found."""
    self.mock_get_clusters.return_value = []
    step = node_bootstrapping.NodeBootstrappingStart()
    with op.operator_context(self.mock_op_parent):
      step.execute()
    self.op_add_skipped.assert_called_with(
        ANY, reason='No test-cluster GKE cluster found in project test-project')

  def test_start_no_clusters_at_all(self):
    """No clusters in project."""
    self.params[flags.GKE_CLUSTER_NAME] = None
    self.mock_get_clusters.return_value = []
    step = node_bootstrapping.NodeBootstrappingStart()
    with op.operator_context(self.mock_op_parent):
      step.execute()
    self.op_add_skipped.assert_called_with(
        ANY, reason='No GKE clusters found in project test-project')

  def test_start_non_gke_node(self):
    """Node is not a GKE node."""
    self.mock_get_instance.return_value = self.create_mock_vm(is_gke=False)
    step = node_bootstrapping.NodeBootstrappingStart()
    with op.operator_context(self.mock_op_parent):
      step.execute()
    self.op_add_skipped.assert_called_with(
        ANY,
        reason=
        'Instance test-node in location us-central1-a does not appear to be a GKE node'
    )

  def test_insert_check_failed(self):
    """instances.insert error found."""
    self.params[flags.NODE] = None  # Ensure it checks pool insert
    self.mock_realtime_query.return_value = [{
        'severity': 'ERROR',
        'protoPayload': {
            'resourceName': 'pool'
        }
    }]
    step = node_bootstrapping.NodeInsertCheck()
    with op.operator_context(self.mock_op_parent):
      step.execute()
    self.op_add_failed.assert_called_once()

  def test_registration_too_young(self):
    """Node just booted (< 7 mins)."""
    vm = self.create_mock_vm()
    vm.creation_timestamp = TEST_TIME - timedelta(minutes=2)
    self.mock_get_instance.return_value = vm
    step = node_bootstrapping.NodeRegistrationSuccess()
    with op.operator_context(self.mock_op_parent):
      step.execute()
    self.op_add_failed.assert_called_with(ANY, reason=ANY, remediation=ANY)

  def test_registration_missing_permissions(self):
    """Node SA lacks log writer role."""
    vm = self.create_mock_vm()
    self.mock_get_instance.return_value = vm
    mock_policy = MagicMock()
    mock_policy.has_role_permissions.return_value = False
    self.mock_get_project_policy.return_value = mock_policy
    step = node_bootstrapping.NodeRegistrationSuccess()
    with op.operator_context(self.mock_op_parent):
      step.execute()
    self.op_add_failed.assert_called_with(ANY, reason=ANY, remediation=ANY)

  def test_registration_repair_loop(self):
    """NRC finished for name but not current ID."""
    vm = self.create_mock_vm()
    self.mock_get_instance.return_value = vm
    self.mock_realtime_query.side_effect = [
        [],  # for log_entries_success
        [],  # for log_entries_completed by id
        [{
            'textPayload': 'Completed running Node Registration Checker'
        }],
        [
            {
                'textPayload': 'other log'
            },
            {
                'textPayload':
                    '** Here is a summary of the checks performed: **'
            },
            {
                'textPayload': 'check 1'
            },
            {
                'textPayload':
                    ('** Completed running Node Registration Checker **')
            },
        ],
    ]
    step = node_bootstrapping.NodeRegistrationSuccess()
    with op.operator_context(self.mock_op_parent):
      step.execute()
    self.op_add_failed.assert_called()

  def test_registration_deleted_node_past_success(self):
    """Node deleted but registered in past."""
    self.mock_get_instance.return_value = None
    self.mock_realtime_query.return_value = [{
        'textPayload': 'Node ready and registered.'
    }]
    step = node_bootstrapping.NodeRegistrationSuccess()
    with op.operator_context(self.mock_op_parent):
      step.execute()
    self.op_add_ok.assert_called()

  def test_get_nrc_summary_logic(self):
    """Directly tests the helper logic of get_nrc_summary."""
    self.mock_realtime_query.return_value = [
        {
            'textPayload': 'other log'
        },
        {
            'textPayload': '** Here is a summary of the checks performed: **'
        },
        {
            'textPayload': 'check 1'
        },
        {
            'textPayload': '** Completed running Node Registration Checker **'
        },
    ]
    with op.operator_context(self.mock_op_parent):
      summary = node_bootstrapping.get_nrc_summary('node', 'zone')
    self.assertEqual(len(summary), 3)
    self.assertIn('check 1', summary[1])

  def test_insert_check_ok(self):
    """No insert errors found for nodepool."""
    self.params[flags.NODE] = None
    self.mock_realtime_query.return_value = []
    step = node_bootstrapping.NodeInsertCheck()
    with op.operator_context(self.mock_op_parent):
      step.execute()
    self.op_add_ok.assert_called_once()

  def test_registration_start_time_after_boot(self):
    """node_start_time < START_TIME failure."""
    vm = self.create_mock_vm()
    vm.creation_timestamp = datetime(2024, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
    self.mock_get_instance.return_value = vm
    self.params[flags.START_TIME] = datetime(2024,
                                             1,
                                             2,
                                             0,
                                             0,
                                             0,
                                             tzinfo=timezone.utc)
    mock_policy = MagicMock()
    mock_policy.has_role_permissions.return_value = True
    self.mock_get_project_policy.return_value = mock_policy
    step = node_bootstrapping.NodeRegistrationSuccess()
    with op.operator_context(self.mock_op_parent):
      step.execute()
    self.op_add_failed.assert_called_with(ANY, reason=ANY, remediation=ANY)

  def test_registration_success_running(self):
    """Running node registered successfully."""
    vm = self.create_mock_vm()
    self.mock_get_instance.return_value = vm
    self.mock_realtime_query.return_value = [{
        'textPayload': 'Node ready and registered.'
    }]
    mock_policy = MagicMock()
    mock_policy.has_role_permissions.return_value = True
    self.mock_get_project_policy.return_value = mock_policy
    step = node_bootstrapping.NodeRegistrationSuccess()
    with op.operator_context(self.mock_op_parent):
      step.execute()
    self.op_add_ok.assert_called()

  def test_registration_failed_with_summary(self):
    """Checker completed but failed, summary extracted."""
    vm = self.create_mock_vm()
    self.mock_get_instance.return_value = vm
    mock_policy = MagicMock()
    mock_policy.has_role_permissions.return_value = True
    self.mock_get_project_policy.return_value = mock_policy
    self.mock_realtime_query.side_effect = [
        [],  # for log_entries_success
        [{
            'textPayload': 'Completed...'
        }],  # for log_entries_completed
        [  # for log_entries_all for summary extraction
            {
                'textPayload': 'Completed running Node Registration Checker'
            },
            {
                'textPayload': 'Error details'
            },
            {
                'textPayload': node_bootstrapping.TOKEN_NRC_START
            },
        ]
    ]

    step = node_bootstrapping.NodeRegistrationSuccess()
    with op.operator_context(self.mock_op_parent):
      step.execute()
    self.op_add_failed.assert_called()

  def test_registration_deleted_node_failed_summary(self):
    """Node not running, checker failed in past."""
    self.mock_get_instance.return_value = None
    self.mock_realtime_query.side_effect = [
        [],  # log_entries_success
        [{
            'textPayload': 'Completed...'
        }],  # log_entries_completed by name
        [  # logs for get_nrc_summary
            {
                'textPayload': node_bootstrapping.TOKEN_NRC_START
            },
            {
                'textPayload': 'error'
            },
            {
                'textPayload':
                    '** Completed running Node Registration Checker **'
            },
        ]
    ]
    step = node_bootstrapping.NodeRegistrationSuccess()
    with op.operator_context(self.mock_op_parent):
      step.execute()
    self.op_add_failed.assert_called()

  def test_end_step_not_satisfied(self):
    """User not satisfied with analysis."""
    with patch('gcpdiag.runbook.op.prompt', return_value=op.NO):
      op_info = patch('gcpdiag.runbook.op.info').start()
      step = node_bootstrapping.NodeBootstrappingEnd()
      with op.operator_context(self.mock_op_parent):
        step.execute()
      op_info.assert_called_with(message=ANY)

  def test_get_nrc_summary_no_match(self):
    """get_nrc_summary with no summary tokens."""
    self.mock_realtime_query.return_value = [{'textPayload': 'junk'}]
    with op.operator_context(self.mock_op_parent):
      summary = node_bootstrapping.get_nrc_summary('node', 'zone')
      self.assertEqual(len(summary), 0)

  def test_get_instance_http_error(self):
    """gce.get_instance raises HttpError."""
    self.mock_get_instance.side_effect = HttpError(MagicMock(status=404),
                                                   b'not found')
    self.mock_realtime_query.return_value = []
    step = node_bootstrapping.NodeBootstrappingStart()
    with op.operator_context(self.mock_op_parent):
      step.execute()
    self.op_add_skipped.assert_called_once()
    _, kwargs = self.op_add_skipped.call_args
    self.assertIn('There are no log entries for the provided node test-node',
                  kwargs['reason'])

  def test_start_no_logs_for_node(self):
    """No audit logs found for the node."""
    self.mock_get_instance.return_value = self.create_mock_vm()
    self.mock_realtime_query.return_value = []
    step = node_bootstrapping.NodeBootstrappingStart()
    with op.operator_context(self.mock_op_parent):
      step.execute()
    self.op_add_skipped.assert_called_once()
    _, kwargs = self.op_add_skipped.call_args
    self.assertIn('There are no log entries for the provided node test-node',
                  kwargs['reason'])

  def test_registration_uncertain_no_nrc_complete(self):
    """NRC completion log not found for running node."""
    vm = self.create_mock_vm()
    self.mock_get_instance.return_value = vm
    mock_policy = MagicMock()
    mock_policy.has_role_permissions.return_value = True
    self.mock_get_project_policy.return_value = mock_policy
    self.mock_realtime_query.side_effect = [
        [],  # log_entries_success
        [],  # log_entries_completed by id
        []  # log_entries_completed by name
    ]
    step = node_bootstrapping.NodeRegistrationSuccess()
    with op.operator_context(self.mock_op_parent):
      step.execute()
    self.op_add_failed.assert_called_with(ANY, reason=ANY, remediation=ANY)

  def test_node_not_running_nrc_did_not_complete_in_past(self):
    """Node not running, NRC never completed in past."""
    self.mock_get_instance.return_value = None
    self.mock_realtime_query.side_effect = [
        [],  # log_entries_success
        []  # log_entries_completed by name
    ]
    step = node_bootstrapping.NodeRegistrationSuccess()
    with op.operator_context(self.mock_op_parent):
      step.execute()
    self.op_add_failed.assert_called_with(ANY, reason=ANY, remediation=ANY)

  def test_legacy_parameter_handler(self):
    """legacy 'name' parameter is handled."""
    runbook = node_bootstrapping.NodeBootstrapping()
    params = {'name': 'test-cluster'}
    runbook.legacy_parameter_handler(params)
    self.assertNotIn('name', params)
    self.assertIn('gke_cluster_name', params)
    self.assertEqual(params['gke_cluster_name'], 'test-cluster')

  def test_build_tree(self):
    """build_tree."""
    runbook = node_bootstrapping.NodeBootstrapping()
    runbook.build_tree()
    # BFS to collect all steps
    q = collections.deque([runbook.start])
    steps_in_runbook = []
    visited_steps = set()
    while q:
      s = q.popleft()
      if s in visited_steps:
        continue
      visited_steps.add(s)
      steps_in_runbook.append(s)
      q.extend(s.steps)
    step_types = [type(s) for s in steps_in_runbook]
    self.assertIn(node_bootstrapping.NodeBootstrappingStart, step_types)
    self.assertIn(node_bootstrapping.NodeInsertCheck, step_types)
    self.assertIn(node_bootstrapping.NodeRegistrationSuccess, step_types)
    self.assertIn(node_bootstrapping.NodeBootstrappingEnd, step_types)


if __name__ == '__main__':
  unittest.main()
