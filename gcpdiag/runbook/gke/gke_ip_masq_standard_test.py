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
"""Test class for gke/GkeIpMasqStandard."""

import unittest
from unittest import mock

from gcpdiag.queries import apis_stub
from gcpdiag.runbook import op
from gcpdiag.runbook.gke import flags, gke_ip_masq_standard


class MockMessage:
  """Mock messages for testing."""

  def get_msg(self, key, **kwargs):
    del kwargs
    return f'{key}'


class TestGkeIpMasqStandard(unittest.TestCase):
  """Unit tests for GkeIpMasqStandard runbook logic."""

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
    self.project_path = 'projects/p1'
    self.cluster_c1 = mock.Mock()
    self.cluster_c1.__str__ = mock.Mock(
        return_value='projects/p1/locations/us-central1/clusters/c1')
    self.clusters = {'c1': self.cluster_c1}
    self.enterContext(
        mock.patch('gcpdiag.runbook.op.get_context', autospec=True))
    self.enterContext(
        mock.patch('gcpdiag.runbook.op.prep_msg',
                   side_effect=lambda x, **y: x,
                   autospec=True))

  @mock.patch('gcpdiag.queries.crm.get_project')
  @mock.patch('gcpdiag.queries.gke.get_clusters')
  @mock.patch('gcpdiag.runbook.op.get')
  @mock.patch('gcpdiag.runbook.op.add_ok')
  def test_execute_found_cluster_with_name_and_location(self, mock_add_ok,
                                                        mock_op_get,
                                                        mock_get_clusters,
                                                        mock_get_project):
    """StartStep adds OK when both cluster name and location match an existing cluster."""
    mock_get_project.return_value = self.project_path
    mock_get_clusters.return_value = self.clusters
    mock_op_get.side_effect = {
        flags.PROJECT_ID: 'p1',
        flags.GKE_CLUSTER_NAME: 'c1',
        flags.LOCATION: 'us-central1'
    }.get
    step = gke_ip_masq_standard.GkeIpMasqStandardStart()

    step.execute()

    mock_add_ok.assert_called_once()

  @mock.patch('gcpdiag.queries.crm.get_project')
  @mock.patch('gcpdiag.queries.gke.get_clusters')
  @mock.patch('gcpdiag.runbook.op.get')
  @mock.patch('gcpdiag.runbook.op.add_skipped')
  def test_execute_skipped_when_cluster_location_mismatch(
      self, mock_add_skipped, mock_op_get, mock_get_clusters, mock_get_project):
    """StartStep skips when the cluster name exists but is in a different location."""
    mock_get_project.return_value = self.project_path
    mock_get_clusters.return_value = self.clusters
    mock_op_get.side_effect = {
        flags.PROJECT_ID: 'p1',
        flags.GKE_CLUSTER_NAME: 'c1',
        flags.LOCATION: 'europe-west1'
    }.get
    step = gke_ip_masq_standard.GkeIpMasqStandardStart()

    step.execute()

    mock_add_skipped.assert_called_with(self.project_path, reason=mock.ANY)

  @mock.patch('gcpdiag.queries.crm.get_project')
  @mock.patch('gcpdiag.queries.gke.get_clusters')
  @mock.patch('gcpdiag.runbook.op.get')
  @mock.patch('gcpdiag.runbook.op.add_uncertain')
  def test_execute_uncertain_when_only_location_provided(
      self, mock_add_uncertain, mock_op_get, mock_get_clusters,
      mock_get_project):
    """StartStep adds uncertain when only location is provided and multiple clusters exist."""
    mock_get_project.return_value = self.project_path
    mock_get_clusters.return_value = self.clusters
    mock_op_get.side_effect = {
        flags.PROJECT_ID: 'p1',
        flags.GKE_CLUSTER_NAME: None,
        flags.LOCATION: 'us-central1'
    }.get
    step = gke_ip_masq_standard.GkeIpMasqStandardStart()

    step.execute()

    mock_add_uncertain.assert_called_once()

  def test_legacy_parameter_handler_converts_name_to_cluster_name(self):
    """legacy_parameter_handler correctly moves 'name' to 'gke_cluster_name'."""
    runbook_obj = gke_ip_masq_standard.GkeIpMasqStandard()
    params = {flags.NAME: 'test_cluster'}

    runbook_obj.legacy_parameter_handler(params)

    self.assertNotIn(flags.NAME, params)
    self.assertEqual(params[flags.GKE_CLUSTER_NAME], 'test_cluster')

  @mock.patch('gcpdiag.runbook.DiagnosticTree.add_step')
  @mock.patch('gcpdiag.runbook.DiagnosticTree.add_start')
  @mock.patch('gcpdiag.runbook.DiagnosticTree.add_end')
  def test_build_tree_constructs_full_diagnostic_path(self, mock_add_end,
                                                      mock_add_start,
                                                      mock_add_step):
    """build_tree adds all required steps and end states to the tree."""
    runbook_obj = gke_ip_masq_standard.GkeIpMasqStandard()

    runbook_obj.build_tree()
    mock_add_start.assert_called_once()
    mock_add_end.assert_called_once()
    self.assertGreater(mock_add_step.call_count, 1)

  @mock.patch('gcpdiag.queries.crm.get_project')
  @mock.patch('gcpdiag.queries.logs.realtime_query')
  @mock.patch('gcpdiag.runbook.op.get')
  @mock.patch('gcpdiag.runbook.op.add_ok')
  def test_nodeproblem_success_on_logs_found(self, mock_add_ok, mock_op_get,
                                             mock_realtime_query,
                                             mock_get_project):
    """Nodeproblem adds OK when flow logs are found."""
    mock_get_project.return_value = self.project_path
    mock_realtime_query.return_value = ['log_entry']
    mock_op_get.return_value = 'some_val'
    step = gke_ip_masq_standard.Nodeproblem()

    step.execute()

    mock_add_ok.assert_called_once()


class TestGkeIpMasqStandardCoverage(unittest.TestCase):
  """unit tests to increase coverage of gke_ip_masq_standard.py."""

  def setUp(self):
    super().setUp()
    self.project_path = 'projects/p1'
    self.cluster_c1 = mock.Mock()
    self.cluster_c1.__str__ = mock.Mock(
        return_value='projects/p1/locations/us-central1/clusters/c1')
    self.clusters = {'c1': self.cluster_c1}
    self.enterContext(
        mock.patch('gcpdiag.runbook.op.get_context', autospec=True))
    self.enterContext(
        mock.patch('gcpdiag.runbook.op.prep_msg',
                   side_effect=lambda x, **y: x,
                   autospec=True))

  @mock.patch('gcpdiag.queries.crm.get_project')
  @mock.patch('gcpdiag.queries.gke.get_clusters')
  @mock.patch('gcpdiag.runbook.op.get')
  @mock.patch('gcpdiag.runbook.op.add_ok')
  def test_execute_found_cluster_by_name_only(self, mock_add_ok, mock_op_get,
                                              mock_get_clusters,
                                              mock_get_project):
    """GkeIpMasqStandardStart finds cluster when only name is provided (Lines 162-168)."""
    mock_get_project.return_value = self.project_path
    mock_get_clusters.return_value = self.clusters
    mock_op_get.side_effect = {
        flags.PROJECT_ID: 'p1',
        flags.GKE_CLUSTER_NAME: 'c1',
        flags.LOCATION: None
    }.get
    step = gke_ip_masq_standard.GkeIpMasqStandardStart()
    step.execute()
    mock_add_ok.assert_called_with(self.project_path, reason=mock.ANY)

  @mock.patch('gcpdiag.queries.crm.get_project')
  @mock.patch('gcpdiag.queries.gke.get_clusters')
  @mock.patch('gcpdiag.runbook.op.get')
  @mock.patch('gcpdiag.runbook.op.add_skipped')
  def test_execute_skipped_when_cluster_name_not_found(self, mock_add_skipped,
                                                       mock_op_get,
                                                       mock_get_clusters,
                                                       mock_get_project):
    """GkeIpMasqStandardStart skips when cluster name is provided but not found (Line 187)."""
    mock_get_project.return_value = self.project_path
    mock_get_clusters.return_value = {}
    mock_op_get.side_effect = {
        flags.PROJECT_ID: 'p1',
        flags.GKE_CLUSTER_NAME: 'missing-cluster',
        flags.LOCATION: None
    }
    step = gke_ip_masq_standard.GkeIpMasqStandardStart()
    step.execute()
    mock_add_skipped.assert_called_with(self.project_path, reason=mock.ANY)

  @mock.patch('gcpdiag.queries.crm.get_project')
  @mock.patch('gcpdiag.queries.gke.get_clusters')
  @mock.patch('gcpdiag.runbook.op.get')
  @mock.patch('gcpdiag.runbook.op.add_skipped')
  def test_execute_skipped_when_no_clusters_at_location(self, mock_add_skipped,
                                                        mock_op_get,
                                                        mock_get_clusters,
                                                        mock_get_project):
    """GkeIpMasqStandardStart skips when no clusters exist at the provided location (Line 193)."""
    mock_get_project.return_value = self.project_path
    mock_get_clusters.return_value = {}
    mock_op_get.side_effect = {
        flags.PROJECT_ID: 'p1',
        flags.GKE_CLUSTER_NAME: None,
        flags.LOCATION: 'us-central1'
    }.get
    step = gke_ip_masq_standard.GkeIpMasqStandardStart()
    step.execute()
    mock_add_skipped.assert_called_with(self.project_path, reason=mock.ANY)

  @mock.patch('gcpdiag.queries.crm.get_project')
  @mock.patch('gcpdiag.queries.logs.realtime_query')
  @mock.patch('gcpdiag.runbook.op.get')
  @mock.patch('gcpdiag.runbook.op.add_failed')
  def test_nodeproblem_failed_on_no_logs(self, mock_add_failed, mock_op_get,
                                         mock_realtime_query, mock_get_project):
    """Nodeproblem fails when no VPC flow logs are found."""
    mock_get_project.return_value = self.project_path
    mock_realtime_query.return_value = []
    mock_op_get.return_value = 'val'
    step = gke_ip_masq_standard.Nodeproblem()
    step.execute()
    mock_add_failed.assert_called_once()

  @mock.patch('gcpdiag.queries.crm.get_project')
  @mock.patch('gcpdiag.runbook.op.get')
  @mock.patch('gcpdiag.runbook.op.add_uncertain')
  def test_diagnostic_steps_uncertain_output(self, mock_add_uncertain,
                                             mock_op_get, mock_get_project):
    """Verifies all check steps provide uncertain findings (Lines 236, 256, 274, 292, 310)."""
    mock_get_project.return_value = self.project_path
    mock_op_get.return_value = 'p1'

    steps = [
        gke_ip_masq_standard.CheckDaemonSet(),
        gke_ip_masq_standard.CheckConfigMap(),
        gke_ip_masq_standard.CheckPodIP(),
        gke_ip_masq_standard.CheckNodeIP(),
        gke_ip_masq_standard.CheckDestinationIP()
    ]
    for step in steps:
      step.execute()

    self.assertEqual(mock_add_uncertain.call_count, len(steps))

  @mock.patch('gcpdiag.runbook.op.info')
  def test_gke_ip_masq_standard_end_info(self, mock_op_info):
    """GkeIpMasqStandardEnd provides final troubleshooting guidance (Line 328)."""
    step = gke_ip_masq_standard.GkeIpMasqStandardEnd()
    step.execute()
    mock_op_info.assert_called_once_with(message=mock.ANY)
