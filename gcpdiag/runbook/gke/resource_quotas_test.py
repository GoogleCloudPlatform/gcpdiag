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
"""Test class for gke/ResourceQuotas"""

import unittest
from unittest import mock

from gcpdiag import config
from gcpdiag.queries import apis_stub
from gcpdiag.runbook import gke, op, snapshot_test_base
from gcpdiag.runbook.gke import flags, resource_quotas
from gcpdiag.utils import GcpApiError, Version


class Test(snapshot_test_base.RulesSnapshotTestBase):
  rule_pkg = gke
  runbook_name = 'gke/resource-quotas'
  config.init({'auto': True, 'interface': 'cli'})

  rule_parameters = [{
      'project_id': 'gcpdiag-gke-cluster-autoscaler-rrrr',
      'gke_cluster_name': 'gcp-cluster',
      'location': 'europe-west10-a',
      'end_time': '2024-12-09T07:40:16Z',
      'start_time': '2024-12-08T07:40:16Z',
  }]


class MockMessage:
  """Mock messages for testing."""

  def get_msg(self, key, **kwargs):
    del kwargs
    return f'{key}'


class TestResourceQuotas(unittest.TestCase):
  """Unit tests covering resource_quotas."""

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
    self.mock_op_prompt = self.enterContext(
        mock.patch('gcpdiag.runbook.op.prompt'))
    self.mock_op_info = self.enterContext(mock.patch('gcpdiag.runbook.op.info'))
    self.mock_op_prep_msg = self.enterContext(
        mock.patch('gcpdiag.runbook.op.prep_msg'))
    self.mock_crm_get_project = self.enterContext(
        mock.patch('gcpdiag.queries.crm.get_project'))
    self.mock_gke_get_cluster = self.enterContext(
        mock.patch('gcpdiag.queries.gke.get_cluster'))

    self.params = {
        flags.PROJECT_ID: 'test-project',
        flags.GKE_CLUSTER_NAME: 'test-cluster',
        flags.LOCATION: 'us-central1-a',
        flags.START_TIME: '2025-01-01T00:00:00Z',
        flags.END_TIME: '2025-01-01T01:00:00Z',
    }
    self.mock_op_get.side_effect = lambda k: self.params[k]

    self.mock_project = mock.Mock()
    self.mock_project.full_path = 'projects/test-project'
    self.mock_crm_get_project.return_value = self.mock_project

    mock_interface = mock.Mock()
    operator = op.Operator(mock_interface)
    operator.set_parameters(self.params)
    self.enterContext(op.operator_context(operator))

  def test_legacy_parameter_handler_renames_name_to_cluster_name(self):
    """legacy_parameter_handler should map 'name' to 'gke_cluster_name'."""
    rq = resource_quotas.ResourceQuotas()
    parameters = {flags.NAME: 'my-cluster'}
    rq.legacy_parameter_handler(parameters)
    self.assertNotIn(flags.NAME, parameters)
    self.assertEqual(parameters[flags.GKE_CLUSTER_NAME], 'my-cluster')

  def test_build_tree_correctly_assembles_diagnostic_dag(self):
    """build_tree should add steps to the diagnostic tree."""
    rq = resource_quotas.ResourceQuotas()
    rq.build_tree()
    self.assertIsNotNone(rq.start)

  def test_start_step_cluster_found_reports_ok(self):
    """ResourceQuotasStart reports OK when the cluster exists."""
    step = resource_quotas.ResourceQuotasStart()
    self.mock_gke_get_cluster.return_value = mock.Mock(name='my-cluster')
    step.execute()
    self.mock_op_add_ok.assert_called_once()

  def test_start_step_cluster_not_found_reports_skipped(self):
    """ResourceQuotasStart reports SKIPPED when GcpApiError occurs."""
    step = resource_quotas.ResourceQuotasStart()
    self.mock_gke_get_cluster.side_effect = GcpApiError('not found')
    step.execute()
    self.mock_op_add_skipped.assert_called_once()

  def test_cluster_version_step_assigns_higher_version_template(self):
    """ClusterVersion uses higher_version template for GKE versions >= 1.28."""
    step = resource_quotas.ClusterVersion()
    self.mock_gke_get_cluster.return_value = mock.Mock(
        master_version=Version('1.28.0'), name='c', location='l')
    step.add_child = mock.Mock()
    step.execute()
    child = step.add_child.call_args[0][0]
    self.assertEqual(child.template,
                     'resourcequotas::higher_version_quota_exceeded')

  def test_cluster_version_step_assigns_lower_version_template(self):
    """ClusterVersion uses lower_version template for GKE versions < 1.28."""
    step = resource_quotas.ClusterVersion()
    self.mock_gke_get_cluster.return_value = mock.Mock(
        master_version=Version('1.27.0'), name='c', location='l')
    step.add_child = mock.Mock()
    step.execute()
    child = step.add_child.call_args[0][0]
    self.assertEqual(child.template,
                     'resourcequotas::lower_version_quota_exceeded')

  @mock.patch('gcpdiag.queries.logs.realtime_query')
  def test_quota_exceeded_step_reports_failure_when_logs_found(
      self, mock_logs_query):
    """ResourceQuotaExceeded reports FAILURE when quota logs are identified."""
    step = resource_quotas.ResourceQuotaExceeded()
    step.project_id, step.cluster_name, step.cluster_location = 'p', 'c', 'l'
    self.mock_crm_get_project.return_value = mock.Mock(project_id='p')
    mock_logs_query.return_value = [{
        'protoPayload': {
            'status': {
                'message': 'exceeded quota'
            }
        }
    }]
    step.execute()
    self.mock_op_add_failed.assert_called_once()

  @mock.patch('gcpdiag.queries.logs.realtime_query')
  def test_quota_exceeded_step_reports_ok_when_no_logs_found(
      self, mock_logs_query):
    """ResourceQuotaExceeded reports OK when no relevant logs are found."""
    step = resource_quotas.ResourceQuotaExceeded()
    step.project_id, step.cluster_name, step.cluster_location = 'p', 'c', 'l'
    self.mock_crm_get_project.return_value = mock.Mock(project_id='p')
    mock_logs_query.return_value = []
    step.execute()
    self.mock_op_add_ok.assert_called_once()

  def test_end_step_shows_info_on_negative_user_response(self):
    """ResourceQuotasEnd displays end message when user responds 'NO'."""
    step = resource_quotas.ResourceQuotasEnd()
    self.mock_op_prompt.return_value = resource_quotas.op.NO
    step.execute()
    self.mock_op_info.assert_called_once_with(
        message=resource_quotas.op.END_MESSAGE)
