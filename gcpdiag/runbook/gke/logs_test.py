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
"""Test class for gke/GkeLogs"""

import datetime
import unittest
from unittest import mock

from gcpdiag import config
from gcpdiag.queries import apis_stub
from gcpdiag.runbook import gke as gke_runbook
from gcpdiag.runbook import op, snapshot_test_base
from gcpdiag.runbook.gke import flags, logs


class MockMessage:
  """Mock messages for testing."""

  def get_msg(self, key, **kwargs):
    del kwargs
    return f'{key}'


class Test(snapshot_test_base.RulesSnapshotTestBase):
  rule_pkg = gke_runbook
  runbook_name = 'gke/logs'
  project_id = 'gcpdiag-gke-cluster-autoscaler-rrrr'
  config.init({'auto': True, 'interface': 'cli'}, project_id)

  rule_parameters = [{
      'project_id': 'gcpdiag-gke-cluster-autoscaler-rrrr',
      'name': 'gcp-cluster',
      'gke_cluster_name': 'gcp-cluster',
      'location': 'europe-west10'
  }]


class TestGkeLogsSteps(unittest.TestCase):
  """Unit tests for GKE Logs runbook steps to increase coverage."""

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
    self.mock_op_get = self.enterContext(mock.patch('gcpdiag.runbook.op.get'))
    self.mock_op_add_ok = self.enterContext(
        mock.patch('gcpdiag.runbook.op.add_ok'))
    self.mock_op_add_failed = self.enterContext(
        mock.patch('gcpdiag.runbook.op.add_failed'))
    self.mock_op_add_skipped = self.enterContext(
        mock.patch('gcpdiag.runbook.op.add_skipped'))
    self.mock_crm_get_project = self.enterContext(
        mock.patch('gcpdiag.queries.crm.get_project'))
    self.mock_gke_get_clusters = self.enterContext(
        mock.patch('gcpdiag.queries.gke.get_clusters'))

    self.project_id = 'test-project'
    self.params = {
        flags.PROJECT_ID: self.project_id,
        flags.GKE_CLUSTER_NAME: 'test-cluster',
        flags.LOCATION: 'us-central1'
    }
    self.mock_op_get.side_effect = lambda key, default=None: self.params.get(
        key, default)
    self.mock_interface = mock.MagicMock()
    self.operator = op.Operator(self.mock_interface)
    self.operator.set_parameters(self.params)
    self.operator.set_step(mock.MagicMock())
    self.operator.set_run_id('test_run')

  # Tests for LogsStart (Lines 83-105)
  def test_logs_start_skips_when_no_clusters(self):
    """Given no clusters in project, when LogsStart executes, then it skips."""
    self.mock_gke_get_clusters.return_value = {}
    step = logs.LogsStart()
    with op.operator_context(self.operator):
      step.execute()
    self.mock_op_add_skipped.assert_called_with(mock.ANY, reason=mock.ANY)

  def test_logs_start_skips_when_cluster_not_found(self):
    """Given cluster name doesn't match, when LogsStart executes, then it skips."""
    cluster = mock.Mock()
    cluster.__str__ = mock.Mock(
        return_value='projects/p/locations/zone/clusters/other-cluster')
    self.mock_gke_get_clusters.return_value = {'other': cluster}
    step = logs.LogsStart()
    with op.operator_context(self.operator):
      step.execute()
    self.mock_op_add_skipped.assert_called()

  # Tests for LoggingApiEnabled (Lines 122-145)
  @mock.patch('gcpdiag.queries.apis.is_enabled')
  def test_logging_api_failed_when_disabled(self, mock_is_enabled):
    """Given Logging API is disabled, then step fails."""
    mock_is_enabled.return_value = False
    step = logs.LoggingApiEnabled()
    with op.operator_context(self.operator):
      step.execute()
    self.mock_op_add_failed.assert_called()

  # Tests for ClusterLevelLoggingEnabled (Lines 148-188)
  @mock.patch('gcpdiag.lint.gke.util.get_cluster_object')
  def test_cluster_logging_fails_when_disabled(self, mock_get_obj):
    """Given logging is disabled in cluster config, then step fails."""
    cluster_obj = mock.Mock()
    cluster_obj.is_autopilot = False
    cluster_obj.has_logging_enabled.return_value = False
    mock_get_obj.return_value = cluster_obj

    step = logs.ClusterLevelLoggingEnabled()
    with op.operator_context(self.operator):
      step.execute()
    self.mock_op_add_failed.assert_called()

  # Tests for NodePoolCloudLoggingAccessScope (Lines 206-224)
  @mock.patch('gcpdiag.lint.gke.util.get_cluster_object')
  def test_nodepool_scope_fails_when_missing(self, mock_get_obj):
    """Given node pool missing logging scope, then step fails."""
    nodepool = mock.Mock()
    nodepool.config.oauth_scopes = ['https://www.googleapis.com/auth/compute']
    cluster_obj = mock.Mock()
    cluster_obj.nodepools = [nodepool]
    mock_get_obj.return_value = cluster_obj

    step = logs.NodePoolCloudLoggingAccessScope()
    with op.operator_context(self.operator):
      step.execute()
    self.mock_op_add_failed.assert_called()

  # Tests for ServiceAccountLoggingPermission (Lines 246-314)
  @mock.patch('gcpdiag.queries.iam.get_project_policy')
  @mock.patch('gcpdiag.queries.iam.is_service_account_enabled')
  @mock.patch('gcpdiag.lint.gke.util.get_cluster_object')
  def test_sa_permission_fails_when_missing_role(self, mock_get_obj,
                                                 mock_sa_enabled,
                                                 mock_get_policy):
    """Given SA exists but missing LogWriter role, then step fails."""
    nodepool = mock.Mock()
    nodepool.service_account = 'test-sa@test.iam.gserviceaccount.com'
    cluster_obj = mock.Mock()
    cluster_obj.nodepools = [nodepool]
    mock_get_obj.return_value = cluster_obj
    mock_sa_enabled.return_value = True

    policy = mock.Mock()
    policy.has_role_permissions.return_value = False
    mock_get_policy.return_value = policy

    step = logs.ServiceAccountLoggingPermission()
    with op.operator_context(self.operator):
      step.execute()
    self.mock_op_add_failed.assert_called()

  # Tests for LoggingWriteApiQuotaExceeded (Lines 332-367)
  @mock.patch('gcpdiag.queries.monitoring.query')
  def test_quota_check_fails_when_exceeded(self, mock_query):
    """Given monitoring returns quota exceeded errors, then step fails."""
    self.params[flags.START_TIME] = mock.Mock()
    self.params[flags.END_TIME] = mock.Mock()

    mock_query.return_value = {
        'ts1': {
            'labels': {
                'metric.limit_name': 'WriteRequestsPerMinutePerProject'
            }
        }
    }

    step = logs.LoggingWriteApiQuotaExceeded()
    with op.operator_context(self.operator):
      step.execute()
    self.mock_op_add_failed.assert_called()
    del self.params[flags.START_TIME]
    del self.params[flags.END_TIME]

  # Tests for LogsEnd (Lines 387-392)
  @mock.patch('gcpdiag.runbook.op.prompt')
  def test_logs_end_generates_report_on_no(self, mock_prompt):
    """Given user is not satisfied, then generate report."""
    mock_prompt.return_value = op.NO
    op.interface = self.mock_interface
    step = logs.LogsEnd()
    with op.operator_context(self.operator):
      step.execute()
    self.mock_interface.rm.generate_report.assert_called()
    del op.interface


class TestGkeLogsCoverage(unittest.TestCase):
  """Unit tests targeting uncovered lines in logs.py."""

  def setUp(self):
    super().setUp()
    self.mock_interface = mock.Mock()
    self.operator = op.Operator(self.mock_interface)
    self.params = {
        flags.PROJECT_ID: 'test-project',
        flags.GKE_CLUSTER_NAME: 'test-cluster',
        flags.LOCATION: 'us-central1',
        flags.START_TIME: datetime.datetime.now(),
        flags.END_TIME: datetime.datetime.now()
    }
    self.operator.set_parameters(self.params)
    self.operator.set_step(mock.MagicMock())
    self.operator.set_run_id('test_run')
    self.operator.interface = mock.Mock()
    self.operator.interface.rm = mock.Mock()
    self.operator.messages = MockMessage()
    # Setup standard mocks for gcpdiag operations
    self.mock_op_get = self.enterContext(mock.patch('gcpdiag.runbook.op.get'))
    self.mock_op_get.side_effect = lambda key, default=None: self.params.get(
        key, default)
    self.mock_op_add_ok = self.enterContext(
        mock.patch('gcpdiag.runbook.op.add_ok'))
    self.mock_op_add_failed = self.enterContext(
        mock.patch('gcpdiag.runbook.op.add_failed'))
    self.mock_op_add_skipped = self.enterContext(
        mock.patch('gcpdiag.runbook.op.add_skipped'))
    self.mock_gke_get_clusters = self.enterContext(
        mock.patch('gcpdiag.queries.gke.get_clusters'))
    self.enterContext(mock.patch('gcpdiag.queries.crm.get_project'))
    self.mock_is_enabled = self.enterContext(
        mock.patch('gcpdiag.queries.apis.is_enabled'))
    self.mock_iam_get_project_policy = self.enterContext(
        mock.patch('gcpdiag.queries.iam.get_project_policy'))
    self.mock_iam_is_service_account_enabled = self.enterContext(
        mock.patch('gcpdiag.queries.iam.is_service_account_enabled'))
    self.mock_monitoring_query = self.enterContext(
        mock.patch('gcpdiag.queries.monitoring.query'))
    self.mock_op_prompt = self.enterContext(
        mock.patch('gcpdiag.runbook.op.prompt'))

  # Covers LogsStart (Lines 83-84, 89-105)
  def test_logs_start_branch_coverage(self):
    # Line 83-84: No clusters found
    self.mock_gke_get_clusters.return_value = {}
    step = logs.LogsStart()
    with op.operator_context(self.operator):
      step.execute()
    self.mock_op_add_skipped.assert_called()

    # Line 89-105: Specific cluster mismatch
    cluster = mock.Mock()
    cluster.__str__ = mock.Mock(
        return_value='projects/p/locations/other/clusters/other')
    self.mock_gke_get_clusters.return_value = {'other': cluster}
    with op.operator_context(self.operator):
      step.execute()
    self.mock_op_add_skipped.assert_called()

  # Covers LoggingApiEnabled (Lines 145-146)
  def test_logging_api_failed(self):
    self.mock_is_enabled.return_value = False
    step = logs.LoggingApiEnabled()
    with op.operator_context(self.operator):
      step.execute()
    self.mock_op_add_failed.assert_called()

  # Covers ClusterLevelLoggingEnabled (Lines 155-162, 185)
  @mock.patch('gcpdiag.lint.gke.util.get_cluster_object')
  def test_cluster_logging_disabled_logic(self, mock_get_obj):
    cluster_obj = mock.Mock()
    cluster_obj.is_autopilot = False
    cluster_obj.has_logging_enabled.return_value = True
    cluster_obj.enabled_logging_components.return_value = ['SYSTEM'
                                                          ]  # WORKLOADS missing
    cluster_obj.__str__ = mock.Mock(return_value='test-cluster')
    mock_get_obj.return_value = cluster_obj

    step = logs.ClusterLevelLoggingEnabled()
    with op.operator_context(self.operator):
      step.execute()
    self.mock_op_add_failed.assert_called()

  # Covers NodePoolCloudLoggingAccessScope (Lines 214, 219)
  @mock.patch('gcpdiag.lint.gke.util.get_cluster_object')
  def test_nodepool_scope_coverage(self, mock_get_obj):
    np_ok = mock.Mock()
    np_ok.config.oauth_scopes = [
        'https://www.googleapis.com/auth/logging.write'
    ]
    np_fail = mock.Mock()
    np_fail.config.oauth_scopes = []
    cluster_obj = mock.Mock()
    cluster_obj.nodepools = [np_ok, np_fail]
    mock_get_obj.return_value = cluster_obj

    step = logs.NodePoolCloudLoggingAccessScope()
    with op.operator_context(self.operator):
      step.execute()
    self.mock_op_add_ok.assert_called_with(np_ok, reason=mock.ANY)
    self.mock_op_add_failed.assert_called_with(np_fail,
                                               reason=mock.ANY,
                                               remediation=mock.ANY)

  # Covers ServiceAccountLoggingPermission (Lines 260, 301, 314)
  @mock.patch('gcpdiag.lint.gke.util.get_cluster_object')
  def test_sa_permission_coverage(self, mock_get_obj):
    np_disabled = mock.Mock()
    np_disabled.service_account = 'sa-disabled'
    np_ok = mock.Mock()
    np_ok.service_account = 'sa-ok'
    cluster_obj = mock.Mock()
    cluster_obj.nodepools = [np_disabled, np_ok]
    mock_get_obj.return_value = cluster_obj
    self.mock_iam_is_service_account_enabled.side_effect = lambda sa, ctx: sa == 'sa-ok'
    policy = mock.Mock()
    policy.has_role_permissions.return_value = True
    self.mock_iam_get_project_policy.return_value = policy

    step = logs.ServiceAccountLoggingPermission()
    with op.operator_context(self.operator):
      step.execute()
    self.mock_op_add_failed.assert_called_with(np_disabled,
                                               reason=mock.ANY,
                                               remediation=mock.ANY)
    self.mock_op_add_ok.assert_called_with(np_ok, reason=mock.ANY)

  # Covers LoggingWriteApiQuotaExceeded (Lines 351, 362-365)
  def test_quota_query_error_handling(self):
    # Triggers line 351 (monitoring.query) and 362-365 (KeyError handling)
    self.mock_monitoring_query.return_value = {
        'bad_series': {
            'labels': {
                'metric.limit_name': 'some-limit'
            }
        }
    }  # Missing metric.limit_name
    step = logs.LoggingWriteApiQuotaExceeded()
    with op.operator_context(self.operator):
      step.execute()
    self.mock_op_add_failed.assert_called()

  def test_logs_start_location_mismatch_skips(self):
    """Lines 108-111 (Logic): Skips if no clusters are found at the specified location."""
    # Mock a cluster at a different location than 'us-central1'
    cluster = mock.Mock()
    cluster.__str__ = mock.Mock(
        return_value='projects/p/locations/europe-west1/clusters/c')
    self.mock_gke_get_clusters.return_value = {'cluster': cluster}

    step = logs.LogsStart()
    with op.operator_context(self.operator):
      step.execute()
    self.mock_op_add_skipped.assert_called_once()
    _, kwargs = self.mock_op_add_skipped.call_args
    self.assertIn('does not exist in project', kwargs['reason'])

  @mock.patch('gcpdiag.lint.gke.util.get_cluster_object')
  def test_cluster_logging_enabled_ok(self, mock_get_obj):
    """Line 185: Confirms logging is enabled for non-autopilot clusters."""
    cluster = mock.Mock(is_autopilot=False)
    cluster.has_logging_enabled.return_value = True
    cluster.enabled_logging_components.return_value = ['WORKLOADS', 'SYSTEM']
    mock_get_obj.return_value = cluster
    step = logs.ClusterLevelLoggingEnabled()
    with op.operator_context(self.operator):
      step.execute()
    self.mock_op_add_ok.assert_called()

  @mock.patch('gcpdiag.lint.gke.util.get_cluster_object')
  def test_node_pool_missing_scope_fails(self, mock_get_obj):
    """Line 214: Fails when a node pool is missing required logging scopes."""
    np = mock.Mock()
    np.config.oauth_scopes = [
        'https://www.googleapis.com/auth/compute.readonly'
    ]
    cluster = mock.Mock(nodepools=[np])
    mock_get_obj.return_value = cluster
    step = logs.NodePoolCloudLoggingAccessScope()
    with op.operator_context(self.operator):
      step.execute()
    self.mock_op_add_failed.assert_called()

  def test_node_pool_access_scope_ok(self):
    """Line 214-219 (Logic): Verifies success when a valid logging scope is present."""
    np = mock.Mock()
    np.config.oauth_scopes = ['https://www.googleapis.com/auth/logging.write']
    cluster = mock.Mock(nodepools=[np])

    with mock.patch('gcpdiag.lint.gke.util.get_cluster_object',
                    return_value=cluster):
      step = logs.NodePoolCloudLoggingAccessScope()
      with op.operator_context(self.operator):
        step.execute()
    self.mock_op_add_ok.assert_called()

  @mock.patch('gcpdiag.lint.gke.util.get_cluster_object')
  def test_sa_missing_log_writer_role_fails(self, mock_get_obj):
    """Line 260: Fails when service account lacks roles/logging.logWriter."""
    np = mock.Mock(service_account='test-sa@iam.gserviceaccount.com')
    cluster = mock.Mock(nodepools=[np])
    policy = mock.Mock()
    policy.has_role_permissions.return_value = False
    self.mock_iam_get_project_policy.return_value = policy
    self.mock_iam_is_service_account_enabled.return_value = True
    mock_get_obj.return_value = cluster
    step = logs.ServiceAccountLoggingPermission()
    with op.operator_context(self.operator):
      step.execute()
    self.mock_op_add_failed.assert_called()

  @mock.patch('gcpdiag.lint.gke.util.get_cluster_object')
  def test_sa_disabled_fails(self, mock_get_obj):
    """Lines 254-259 (Logic): Fails when the service account is disabled or deleted."""
    np = mock.Mock(service_account='test-sa@iam.gserviceaccount.com')
    cluster = mock.Mock(nodepools=[np])
    mock_get_obj.return_value = cluster
    self.mock_iam_is_service_account_enabled.return_value = False  # SA is disabled
    step = logs.ServiceAccountLoggingPermission()
    with op.operator_context(self.operator):
      step.execute()
    self.mock_op_add_failed.assert_called_once()
    _, kwargs = self.mock_op_add_failed.call_args
    self.assertIn('is disabled or deleted', kwargs['reason'])

  def test_quota_exceeded_found_fails(self):
    """Line 314: Fails when WriteRequestsPerMinutePerProject quota is exceeded."""
    self.mock_monitoring_query.return_value = {
        'ts1': {
            'labels': {
                'metric.limit_name': 'WriteRequestsPerMinutePerProject'
            }
        }
    }
    step = logs.LoggingWriteApiQuotaExceeded()
    with op.operator_context(self.operator):
      step.execute()
    self.mock_op_add_failed.assert_called()

  def test_quota_exceeded_no_data_ok(self):
    """Lines 301-304 (Logic): Confirms success when no quota-exceeded events are returned."""
    self.mock_monitoring_query.return_value = {}  # Empty results
    step = logs.LoggingWriteApiQuotaExceeded()
    with op.operator_context(self.operator):
      step.execute()
    self.mock_op_add_ok.assert_called()

  def test_logs_end_triggers_report_on_no(self):
    """Line 351: Generates a report if user is not satisfied with the RCA."""
    self.mock_op_prompt.return_value = op.NO
    op.interface = self.operator.interface
    step = logs.LogsEnd()
    with op.operator_context(self.operator):
      step.execute()
    self.operator.interface.rm.generate_report.assert_called()
    del op.interface

  def test_logs_end_satisfied_concludes(self):
    """Line 351 (Logic): Concludes normally when the user is satisfied."""
    self.mock_op_prompt.return_value = op.YES
    step = logs.LogsEnd()
    with op.operator_context(self.operator):
      step.execute()
    # verify generate_report was NOT called
    self.operator.interface.rm.generate_report.assert_not_called()
