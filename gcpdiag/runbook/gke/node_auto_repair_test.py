#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Test class for gke/NodeAutoRepair"""

import unittest
from unittest import mock

from gcpdiag import config
from gcpdiag.queries import apis_stub
from gcpdiag.runbook import gke, op, snapshot_test_base
from gcpdiag.runbook.gke import flags, node_auto_repair


class Test(snapshot_test_base.RulesSnapshotTestBase):
  rule_pkg = gke
  runbook_name = 'gke/node-auto-repair'
  config.init({'auto': True, 'interface': 'cli'})

  rule_parameters = [{
      'project_id': 'gcpdiag-gke-cluster-autoscaler-rrrr',
      'gke_cluster_name': 'gcp-cluster',
      'node': 'gke-gcp-cluster-default-pool-82e0c046-8m8b',
      'location': 'europe-west10-a'
  }]


class MockMessage:
  """Mock messages for testing."""

  def __init__(self):
    self.messages = {
        'nodeautorepair::node_notready': 'Node is not ready',
        'nodeautorepair::node_disk_full': 'Node disk is full',
        'nodeautorepair::unallocatable_gpu': 'Unallocatable GPU',
        'nodeautorepair::unallocatable_tpu': 'Unallocatable TPU',
    }

  def __getitem__(self, key):
    return self.messages[key]


class NodeAutoRepairTest(unittest.TestCase):
  """Test NodeAutoRepair runbook steps and functions."""

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
    operator.messages = MockMessage()
    operator.set_parameters(self.params)
    self.enterContext(op.operator_context(operator))

  @mock.patch('gcpdiag.queries.logs.realtime_query')
  def test_local_realtime_query_calls_logs_query(self, mock_query):
    node_auto_repair.local_realtime_query('test-filter')
    mock_query.assert_called_once()

  @mock.patch('gcpdiag.runbook.gke.node_auto_repair.local_realtime_query')
  def test_unallocatable_gpu_tpu_returns_false_if_no_events(
      self, mock_local_query):
    mock_local_query.return_value = []
    self.assertFalse(node_auto_repair.unallocatable_gpu_tpu('node'))

  @mock.patch('gcpdiag.runbook.gke.node_auto_repair.local_realtime_query')
  def test_unallocatable_gpu_tpu_returns_true_if_gpu_found(
      self, mock_local_query):
    mock_local_query.side_effect = [['event'], ['kubelet']]
    self.assertTrue(node_auto_repair.unallocatable_gpu_tpu('node', gpu=True))

  @mock.patch('gcpdiag.runbook.gke.node_auto_repair.local_realtime_query')
  def test_unallocatable_gpu_tpu_returns_true_if_tpu_found(
      self, mock_local_query):
    mock_local_query.side_effect = [['event'], ['kubelet']]
    self.assertTrue(node_auto_repair.unallocatable_gpu_tpu('node', tpu=True))

  @mock.patch('gcpdiag.runbook.gke.node_auto_repair.local_realtime_query')
  def test_check_node_unhealthy_returns_true_if_logs_found(
      self, mock_local_query):
    mock_local_query.return_value = ['log']
    self.assertTrue(node_auto_repair.check_node_unhealthy('node'))

  @mock.patch('gcpdiag.runbook.gke.node_auto_repair.local_realtime_query')
  def test_check_node_unhealthy_returns_false_if_no_logs(
      self, mock_local_query):
    mock_local_query.return_value = []
    self.assertFalse(node_auto_repair.check_node_unhealthy('node'))

  def test_node_auto_repair_legacy_parameter_handler_renames_flag(self):
    runbook_obj = node_auto_repair.NodeAutoRepair()
    params = {flags.NAME: 'cluster'}
    runbook_obj.legacy_parameter_handler(params)
    self.assertNotIn(flags.NAME, params)
    self.assertIn(flags.GKE_CLUSTER_NAME, params)
    self.assertEqual(params[flags.GKE_CLUSTER_NAME], 'cluster')

  def test_start_step_skips_if_no_clusters_found(self):
    self.mock_gke_get_clusters.return_value = {}
    step = node_auto_repair.NodeAutoRepairStart()
    step.execute()
    self.mock_op_add_skipped.assert_called_once()

  @mock.patch('gcpdiag.runbook.gke.node_auto_repair.local_realtime_query')
  def test_start_step_skips_if_no_repair_operations_found(
      self, mock_local_query):
    self.mock_gke_get_clusters.return_value = {'test-cluster': mock.Mock()}
    mock_local_query.return_value = []
    step = node_auto_repair.NodeAutoRepairStart()
    step.execute()
    self.mock_op_add_skipped.assert_called_once()

  @mock.patch('gcpdiag.runbook.gke.node_auto_repair.local_realtime_query')
  def test_start_step_continues_if_repair_operations_found(
      self, mock_local_query):
    self.mock_gke_get_clusters.return_value = {'test-cluster': mock.Mock()}
    mock_local_query.return_value = ['op']
    step = node_auto_repair.NodeAutoRepairStart()
    step.execute()
    self.mock_op_add_skipped.assert_not_called()

  @mock.patch('gcpdiag.runbook.gke.node_auto_repair.check_node_unhealthy')
  def test_node_not_ready_reports_failure_if_unhealthy(self, mock_check):
    mock_check.return_value = True
    step = node_auto_repair.NodeNotReady()
    step.execute()
    self.mock_op_add_failed.assert_called_once()

  @mock.patch('gcpdiag.runbook.gke.node_auto_repair.check_node_unhealthy')
  def test_node_not_ready_reports_ok_if_healthy(self, mock_check):
    mock_check.return_value = False
    step = node_auto_repair.NodeNotReady()
    step.execute()
    self.mock_op_add_ok.assert_called_once()

  @mock.patch('gcpdiag.runbook.gke.node_auto_repair.check_node_unhealthy')
  def test_node_disk_full_reports_failure_if_pressure_found(self, mock_check):
    mock_check.return_value = True
    step = node_auto_repair.NodeDiskFull()
    step.execute()
    self.mock_op_add_failed.assert_called_once()

  @mock.patch('gcpdiag.runbook.gke.node_auto_repair.unallocatable_gpu_tpu')
  def test_unallocatable_gpu_reports_failure_if_detected(self, mock_check):
    mock_check.return_value = True
    step = node_auto_repair.UnallocatableGpu()
    step.execute()
    self.mock_op_add_failed.assert_called_once()

  @mock.patch('gcpdiag.runbook.gke.node_auto_repair.unallocatable_gpu_tpu')
  def test_unallocatable_tpu_reports_failure_if_detected(self, mock_check):
    mock_check.return_value = True
    step = node_auto_repair.UnallocatableTpu()
    step.execute()
    self.mock_op_add_failed.assert_called_once()

  def test_end_step_finishes_without_info_if_satisfied(self):
    self.mock_op_prompt.return_value = op.YES
    step = node_auto_repair.NodeAutoRepairEnd()
    step.execute()
    self.mock_op_info.assert_not_called()

  def test_end_step_shows_info_if_not_satisfied(self):
    self.mock_op_prompt.return_value = op.NO
    step = node_auto_repair.NodeAutoRepairEnd()
    step.execute()
    self.mock_op_info.assert_called_once()


if __name__ == '__main__':
  unittest.main()
