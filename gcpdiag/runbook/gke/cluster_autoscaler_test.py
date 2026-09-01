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
"""Test class for gke/ClusterAutoscaler."""

import unittest
from unittest import mock

from gcpdiag import config
from gcpdiag.queries import apis_stub
from gcpdiag.runbook import gke, op, snapshot_test_base
from gcpdiag.runbook.gke import cluster_autoscaler
from gcpdiag.utils import GcpApiError


class Test(snapshot_test_base.RulesSnapshotTestBase):
  rule_pkg = gke
  runbook_name = 'gke/cluster-autoscaler'
  config.init({'auto': True, 'interface': 'cli'})

  rule_parameters = [
    {
      'project_id': 'gcpdiag-gke-cluster-autoscaler-rrrr',
      'gke_cluster_name': 'gcp-cluster',
      'location': 'europe-west10',
    }
  ]


RUNBOOK_PARAMS = {
  'project_id': 'gcpdiag-gke-cluster-autoscaler-rrrr',
  'gke_cluster_name': 'gcp-cluster',
  'location': 'europe-west10',
  'start_time': '2024-01-01T00:00:00Z',
  'end_time': '2024-01-01T01:00:00Z',
}


class MockMessage:
  """Mock class for op.Message."""

  def __init__(self):
    self.messages = []

  def print(self, *args, **kwargs):
    pass


class RunbookTest(unittest.TestCase):
  def setUp(self):
    super().setUp()
    self.enterContext(mock.patch('gcpdiag.queries.apis.get_api', new=apis_stub.get_api_stub))
    self.mock_get_user_email = self.enterContext(mock.patch('gcpdiag.queries.apis.get_user_email'))
    self.mock_is_enabled = self.enterContext(mock.patch('gcpdiag.queries.apis.is_enabled'))
    self.mock_is_enabled.return_value = True
    self.mock_get_user_email.return_value = 'test@example.com'

    self.mock_interface = mock.create_autospec(op.InteractionInterface, instance=True)
    self.mock_interface.rm = mock.Mock()
    self.operator = op.Operator(self.mock_interface)
    self.operator.run_id = 'test-run'
    self.operator.messages = MockMessage()
    self.enterContext(mock.patch.object(config, 'get', side_effect=lambda k: RUNBOOK_PARAMS[k]))
    self.mock_op_get = self.enterContext(
      mock.patch.object(op, 'get', side_effect=lambda k, v=None: RUNBOOK_PARAMS[k])
    )
    self.mock_add_ok = self.enterContext(mock.patch.object(op, 'add_ok'))
    self.mock_add_failed = self.enterContext(mock.patch.object(op, 'add_failed'))
    self.mock_add_skipped = self.enterContext(mock.patch.object(op, 'add_skipped'))
    self.mock_crm_get_project = self.enterContext(mock.patch('gcpdiag.queries.crm.get_project'))
    self.mock_gke_get_cluster = self.enterContext(mock.patch('gcpdiag.queries.gke.get_cluster'))
    self.mock_apis_is_enabled = self.enterContext(mock.patch('gcpdiag.queries.apis.is_enabled'))
    self.mock_logs_realtime_query = self.enterContext(
      mock.patch('gcpdiag.queries.logs.realtime_query')
    )
    self.mock_op_prompt = self.enterContext(mock.patch.object(op, 'prompt'))
    self.mock_op_info = self.enterContext(mock.patch.object(op, 'info'))
    self.mock_op_prep_msg = self.enterContext(
      mock.patch.object(op, 'prep_msg', side_effect=lambda x, **y: x)
    )
    self.project = mock.MagicMock()
    self.project.id = RUNBOOK_PARAMS['project_id']
    self.mock_crm_get_project.return_value = self.project
    self.cluster = mock.MagicMock()
    self.cluster.name = RUNBOOK_PARAMS['gke_cluster_name']
    self.mock_gke_get_cluster.return_value = self.cluster

  def test_start_step_logging_disabled(self):
    self.mock_apis_is_enabled.return_value = False
    step = cluster_autoscaler.ClusterAutoscalerStart()
    step.execute()
    self.mock_add_skipped.assert_called_once()

  def test_start_step_cluster_not_found(self):
    """GcpApiError branch."""
    self.mock_apis_is_enabled.return_value = True
    mock_response = mock.Mock()
    mock_response.status = 404
    mock_response.content = b'{"error": "cluster not found"}'
    self.mock_gke_get_cluster.side_effect = GcpApiError(mock_response)
    step = cluster_autoscaler.ClusterAutoscalerStart()
    step.execute()
    self.mock_add_skipped.assert_called_once()

  def test_ca_out_of_resources_step_with_logs(self):
    self.mock_logs_realtime_query.return_value = [{'some': 'log'}]
    step = cluster_autoscaler.CaOutOfResources()
    step.execute()
    self.mock_add_failed.assert_called_once()

  def test_ca_min_size_reached_step_with_logs(self):
    self.mock_logs_realtime_query.return_value = [{'some': 'log'}]
    step = cluster_autoscaler.CaMinSizeReached()
    step.execute()
    self.mock_add_failed.assert_called_once()

  def test_end_step_prompt_no(self):
    self.mock_op_prompt.return_value = op.NO
    step = cluster_autoscaler.ClusterAutoscalerEnd()
    step.execute()
    self.mock_op_info.assert_called_once()

  def test_start_step_success(self):
    self.mock_apis_is_enabled.return_value = True
    self.mock_gke_get_cluster.return_value = self.cluster
    self.mock_gke_get_cluster.side_effect = None
    step = cluster_autoscaler.ClusterAutoscalerStart()
    step.execute()
    self.mock_add_ok.assert_called_once()

  def test_ca_out_of_resources_step_without_logs(self):
    self.mock_logs_realtime_query.return_value = []
    step = cluster_autoscaler.CaOutOfResources()
    step.execute()
    self.mock_add_ok.assert_called_once()

  def test_ca_min_size_reached_step_without_logs(self):
    self.mock_logs_realtime_query.return_value = []
    step = cluster_autoscaler.CaMinSizeReached()
    step.execute()
    self.mock_add_ok.assert_called_once()

  def test_ca_quota_exceeded_step_with_logs(self):
    self.mock_logs_realtime_query.return_value = [{'some': 'log'}]
    step = cluster_autoscaler.CaQuotaExceeded()
    step.execute()
    self.mock_add_failed.assert_called_once()

  def test_ca_quota_exceeded_step_without_logs(self):
    self.mock_logs_realtime_query.return_value = []
    step = cluster_autoscaler.CaQuotaExceeded()
    step.execute()
    self.mock_add_ok.assert_called_once()

  def test_ca_instance_timeout_step_with_logs(self):
    self.mock_logs_realtime_query.return_value = [{'some': 'log'}]
    step = cluster_autoscaler.CaInstanceTimeout()
    step.execute()
    self.mock_add_failed.assert_called_once()

  def test_ca_instance_timeout_step_without_logs(self):
    self.mock_logs_realtime_query.return_value = []
    step = cluster_autoscaler.CaInstanceTimeout()
    step.execute()
    self.mock_add_ok.assert_called_once()

  def test_ca_ip_space_exhausted_step_with_logs(self):
    self.mock_logs_realtime_query.return_value = [{'some': 'log'}]
    step = cluster_autoscaler.CaIpSpaceExhausted()
    step.execute()
    self.mock_add_failed.assert_called_once()

  def test_ca_ip_space_exhausted_step_without_logs(self):
    self.mock_logs_realtime_query.return_value = []
    step = cluster_autoscaler.CaIpSpaceExhausted()
    step.execute()
    self.mock_add_ok.assert_called_once()

  def test_ca_service_account_deleted_step_with_logs(self):
    self.mock_logs_realtime_query.return_value = [{'some': 'log'}]
    step = cluster_autoscaler.CaServiceAccountDeleted()
    step.execute()
    self.mock_add_failed.assert_called_once()

  def test_ca_service_account_deleted_step_without_logs(self):
    self.mock_logs_realtime_query.return_value = []
    step = cluster_autoscaler.CaServiceAccountDeleted()
    step.execute()
    self.mock_add_ok.assert_called_once()

  def test_ca_failed_to_evict_pods_step_with_logs(self):
    self.mock_logs_realtime_query.return_value = [{'some': 'log'}]
    step = cluster_autoscaler.CaFailedToEvictPods()
    step.execute()
    self.mock_add_failed.assert_called_once()

  def test_ca_failed_to_evict_pods_step_without_logs(self):
    self.mock_logs_realtime_query.return_value = []
    step = cluster_autoscaler.CaFailedToEvictPods()
    step.execute()
    self.mock_add_ok.assert_called_once()

  def test_ca_disabled_annotation_step_with_logs(self):
    self.mock_logs_realtime_query.return_value = [{'some': 'log'}]
    step = cluster_autoscaler.CaDisabledAnnotation()
    step.execute()
    self.mock_add_failed.assert_called_once()

  def test_ca_disabled_annotation_step_without_logs(self):
    self.mock_logs_realtime_query.return_value = []
    step = cluster_autoscaler.CaDisabledAnnotation()
    step.execute()
    self.mock_add_ok.assert_called_once()

  def test_ca_min_resource_limit_exceeded_step_with_logs(self):
    self.mock_logs_realtime_query.return_value = [{'some': 'log'}]
    step = cluster_autoscaler.CaMinResourceLimitExceeded()
    step.execute()
    self.mock_add_failed.assert_called_once()

  def test_ca_min_resource_limit_exceeded_step_without_logs(self):
    self.mock_logs_realtime_query.return_value = []
    step = cluster_autoscaler.CaMinResourceLimitExceeded()
    step.execute()
    self.mock_add_ok.assert_called_once()

  def test_ca_no_place_to_move_pods_step_with_logs(self):
    self.mock_logs_realtime_query.return_value = [{'some': 'log'}]
    step = cluster_autoscaler.CaNoPlaceToMovePods()
    step.execute()
    self.mock_add_failed.assert_called_once()

  def test_ca_no_place_to_move_pods_step_without_logs(self):
    self.mock_logs_realtime_query.return_value = []
    step = cluster_autoscaler.CaNoPlaceToMovePods()
    step.execute()
    self.mock_add_ok.assert_called_once()

  def test_ca_pods_not_backed_by_controller_step_with_logs(self):
    self.mock_logs_realtime_query.return_value = [{'some': 'log'}]
    step = cluster_autoscaler.CaPodsNotBackedByController()
    step.execute()
    self.mock_add_failed.assert_called_once()

  def test_ca_pods_not_backed_by_controller_step_without_logs(self):
    self.mock_logs_realtime_query.return_value = []
    step = cluster_autoscaler.CaPodsNotBackedByController()
    step.execute()
    self.mock_add_ok.assert_called_once()

  def test_ca_not_safe_to_evict_annotation_step_with_logs(self):
    self.mock_logs_realtime_query.return_value = [{'some': 'log'}]
    step = cluster_autoscaler.CaNotSafeToEvictAnnotation()
    step.execute()
    self.mock_add_failed.assert_called_once()

  def test_ca_not_safe_to_evict_annotation_step_without_logs(self):
    self.mock_logs_realtime_query.return_value = []
    step = cluster_autoscaler.CaNotSafeToEvictAnnotation()
    step.execute()
    self.mock_add_ok.assert_called_once()

  def test_ca_pod_kube_system_unmovable_step_with_logs(self):
    self.mock_logs_realtime_query.return_value = [{'some': 'log'}]
    step = cluster_autoscaler.CaPodKubeSystemUnmovable()
    step.execute()
    self.mock_add_failed.assert_called_once()

  def test_ca_pod_kube_system_unmovable_step_without_logs(self):
    self.mock_logs_realtime_query.return_value = []
    step = cluster_autoscaler.CaPodKubeSystemUnmovable()
    step.execute()
    self.mock_add_ok.assert_called_once()

  def test_ca_pod_not_enough_pdb_step_with_logs(self):
    self.mock_logs_realtime_query.return_value = [{'some': 'log'}]
    step = cluster_autoscaler.CaPodNotEnoughPdb()
    step.execute()
    self.mock_add_failed.assert_called_once()

  def test_ca_pod_not_enough_pdb_step_without_logs(self):
    self.mock_logs_realtime_query.return_value = []
    step = cluster_autoscaler.CaPodNotEnoughPdb()
    step.execute()
    self.mock_add_ok.assert_called_once()

  def test_ca_pod_controller_not_found_step_with_logs(self):
    self.mock_logs_realtime_query.return_value = [{'some': 'log'}]
    step = cluster_autoscaler.CaPodControllerNotFound()
    step.execute()
    self.mock_add_failed.assert_called_once()

  def test_ca_pod_controller_not_found_step_without_logs(self):
    self.mock_logs_realtime_query.return_value = []
    step = cluster_autoscaler.CaPodControllerNotFound()
    step.execute()
    self.mock_add_ok.assert_called_once()

  def test_ca_pod_unexpected_error_step_with_logs(self):
    self.mock_logs_realtime_query.return_value = [{'some': 'log'}]
    step = cluster_autoscaler.CaPodUnexpectedError()
    step.execute()
    self.mock_add_failed.assert_called_once()

  def test_ca_pod_unexpected_error_step_without_logs(self):
    self.mock_logs_realtime_query.return_value = []
    step = cluster_autoscaler.CaPodUnexpectedError()
    step.execute()
    self.mock_add_ok.assert_called_once()

  def test_legacy_parameter(self):
    params = {'name': 'cluster-1', 'project_id': 'p1', 'location': 'l1'}
    rb = cluster_autoscaler.ClusterAutoscaler()
    rb.legacy_parameter_handler(params)
    self.assertNotIn('name', params)
    self.assertIn('gke_cluster_name', params)
    self.assertEqual(params['gke_cluster_name'], 'cluster-1')


class TestClusterAutoscaler(unittest.TestCase):
  """Unit tests for ClusterAutoscaler runbook to increase coverage."""

  def setUp(self):
    super().setUp()
    self.runbook = cluster_autoscaler.ClusterAutoscaler()

  def test_build_tree_structure(self):
    """Ensures the diagnostic tree is built correctly."""
    self.runbook.build_tree()

    self.assertIsInstance(self.runbook.start, cluster_autoscaler.ClusterAutoscalerStart)

    start_steps = self.runbook.start.steps
    self.assertGreater(len(start_steps), 0)
    self.assertIsInstance(start_steps[0], cluster_autoscaler.CaAutoscalingCheck)

    autoscaling_check_steps = start_steps[0].steps
    self.assertIsInstance(autoscaling_check_steps[0], cluster_autoscaler.CaOutOfResources)

    out_of_resources_steps = autoscaling_check_steps[0].steps
    self.assertIsInstance(out_of_resources_steps[0], cluster_autoscaler.CaQuotaExceeded)

    self.assertIsInstance(self.runbook.start.steps[-1], cluster_autoscaler.ClusterAutoscalerEnd)

  @mock.patch('gcpdiag.queries.apis.is_enabled')
  @mock.patch('gcpdiag.queries.crm.get_project')
  @mock.patch('gcpdiag.queries.gke.get_cluster')
  @mock.patch('gcpdiag.runbook.op.add_skipped')
  @mock.patch('gcpdiag.runbook.op.get')
  def test_start_step_cluster_not_found_mock(
    self, mock_get, mock_add_skipped, mock_gke, mock_crm, mock_apis
  ):
    """GcpApiError branch in ClusterAutoscalerStart.execute."""
    del mock_crm
    mock_get.side_effect = lambda k: 'test-project' if 'project' in k else 'test-cluster'
    mock_apis.return_value = True
    mock_gke.side_effect = GcpApiError(response={'error': {'message': 'Not Found', 'code': 404}})

    step = cluster_autoscaler.ClusterAutoscalerStart()
    step.execute()

    mock_add_skipped.assert_called_once()

  @mock.patch('gcpdiag.runbook.op.prep_msg')
  @mock.patch('gcpdiag.runbook.gke.cluster_autoscaler.local_log_search')
  @mock.patch('gcpdiag.runbook.op.add_failed')
  @mock.patch('gcpdiag.runbook.op.get')
  @mock.patch('gcpdiag.queries.crm.get_project')
  def test_out_of_resources_with_logs(
    self, mock_crm, mock_get, mock_add_failed, mock_log_search, mock_prep_msg
  ):
    """'if log_entries' branch in CaOutOfResources.execute."""
    del mock_crm
    mock_log_search.return_value = [{'textPayload': 'resource exhaustion error'}]
    mock_prep_msg.side_effect = lambda x, **y: x
    mock_get.side_effect = lambda k, v=None: RUNBOOK_PARAMS.get(k, v)
    step = cluster_autoscaler.CaOutOfResources()
    step.execute()

    mock_add_failed.assert_called_once()

  @mock.patch('gcpdiag.runbook.op.prep_msg')
  @mock.patch('gcpdiag.queries.gke.get_cluster')
  @mock.patch('gcpdiag.runbook.op.add_ok')
  @mock.patch('gcpdiag.runbook.op.get')
  @mock.patch('gcpdiag.queries.crm.get_project')
  def test_autoscaling_check_autopilot(
    self, mock_crm, mock_get, mock_add_ok, mock_gke, mock_prep_msg
  ):
    """CaAutoscalingCheck with Autopilot cluster."""
    del mock_crm
    mock_get.side_effect = lambda k, v=None: RUNBOOK_PARAMS.get(k, v)
    mock_cluster = mock.MagicMock()
    mock_cluster.is_autopilot = True
    mock_gke.return_value = mock_cluster

    step = cluster_autoscaler.CaAutoscalingCheck()
    step.execute()
    mock_add_ok.assert_called_once()

  @mock.patch('gcpdiag.runbook.op.prep_msg')
  @mock.patch('gcpdiag.queries.gke.get_cluster')
  @mock.patch('gcpdiag.runbook.op.add_failed')
  @mock.patch('gcpdiag.runbook.op.get')
  @mock.patch('gcpdiag.queries.crm.get_project')
  def test_autoscaling_check_disabled(
    self, mock_crm, mock_get, mock_add_failed, mock_gke, mock_prep_msg
  ):
    """CaAutoscalingCheck when autoscaling is disabled on all pools."""
    del mock_crm
    mock_get.side_effect = lambda k, v=None: RUNBOOK_PARAMS.get(k, v)
    mock_prep_msg.side_effect = lambda x, **y: x

    mock_nodepool = mock.MagicMock()
    mock_nodepool.autoscaling_enabled = False

    mock_cluster = mock.MagicMock()
    mock_cluster.is_autopilot = False
    mock_cluster.nodepools = [mock_nodepool]
    mock_gke.return_value = mock_cluster

    step = cluster_autoscaler.CaAutoscalingCheck()
    step.execute()
    mock_add_failed.assert_called_once()

  @mock.patch('gcpdiag.runbook.op.prep_msg')
  @mock.patch('gcpdiag.queries.gke.get_cluster')
  @mock.patch('gcpdiag.runbook.op.add_failed')
  @mock.patch('gcpdiag.runbook.op.get')
  @mock.patch('gcpdiag.queries.crm.get_project')
  def test_autoscaling_check_limits_reached(
    self, mock_crm, mock_get, mock_add_failed, mock_gke, mock_prep_msg
  ):
    """CaAutoscalingCheck when autoscaling limits are reached (max_node_count)."""
    del mock_crm
    mock_get.side_effect = lambda k, v=None: RUNBOOK_PARAMS.get(k, v)
    mock_prep_msg.side_effect = lambda x, **y: x

    mock_nodepool = mock.MagicMock()
    mock_nodepool.name = 'pool-1'
    mock_nodepool.autoscaling_enabled = True
    mock_nodepool.current_node_count = 10
    mock_nodepool.max_node_count = 10
    mock_nodepool.min_node_count = 1

    mock_cluster = mock.MagicMock()
    mock_cluster.is_autopilot = False
    mock_cluster.nodepools = [mock_nodepool]
    mock_gke.return_value = mock_cluster

    step = cluster_autoscaler.CaAutoscalingCheck()
    step.execute()
    mock_add_failed.assert_called_once()

  @mock.patch('gcpdiag.runbook.op.prep_msg')
  @mock.patch('gcpdiag.queries.gke.get_cluster')
  @mock.patch('gcpdiag.runbook.op.add_ok')
  @mock.patch('gcpdiag.runbook.op.get')
  @mock.patch('gcpdiag.queries.crm.get_project')
  def test_autoscaling_check_zero_nodes_min_zero(
    self, mock_crm, mock_get, mock_add_ok, mock_gke, mock_prep_msg
  ):
    """CaAutoscalingCheck when current=0 and min=0 (should be OK, not limit reached)."""
    del mock_crm
    mock_get.side_effect = lambda k, v=None: RUNBOOK_PARAMS.get(k, v)
    mock_prep_msg.side_effect = lambda x, **y: x

    mock_nodepool = mock.MagicMock()
    mock_nodepool.name = 'pool-1'
    mock_nodepool.autoscaling_enabled = True
    mock_nodepool.current_node_count = 0
    mock_nodepool.max_node_count = 10
    mock_nodepool.min_node_count = 0

    mock_cluster = mock.MagicMock()
    mock_cluster.is_autopilot = False
    mock_cluster.nodepools = [mock_nodepool]
    mock_gke.return_value = mock_cluster

    step = cluster_autoscaler.CaAutoscalingCheck()
    step.execute()
    mock_add_ok.assert_called_once()

  @mock.patch('gcpdiag.runbook.op.prep_msg')
  @mock.patch('gcpdiag.runbook.gke.cluster_autoscaler.local_log_search')
  @mock.patch('gcpdiag.runbook.op.add_failed')
  @mock.patch('gcpdiag.runbook.op.get')
  @mock.patch('gcpdiag.queries.crm.get_project')
  def test_no_scale_up_mig_failing_predicate_logs(
    self, mock_crm, mock_get, mock_add_failed, mock_log_search, mock_prep_msg
  ):
    """CaNoScaleUpMigFailingPredicate parses visibility logs with failing predicate."""
    del mock_crm
    mock_prep_msg.side_effect = lambda x, **y: x
    mock_get.side_effect = lambda k, v=None: RUNBOOK_PARAMS.get(k, v)
    mock_log_search.return_value = [
      {
        'jsonPayload': {
          'noDecisionStatus': {
            'noScaleUp': {
              'unhandledPodGroups': [
                {
                  'podGroup': {'samplePod': {'name': 'web-pod', 'namespace': 'default'}},
                  'rejectedMigs': [
                    {
                      'mig': {'name': 'gke-cluster-pool-1-mig', 'nodepool': 'pool-1'},
                      'reason': {
                        'messageId': 'no.scale.up.mig.failing.predicate',
                        'parameters': ['NodeResourcesFit', 'Taint'],
                      },
                    }
                  ],
                }
              ]
            }
          }
        }
      }
    ]

    step = cluster_autoscaler.CaNoScaleUpMigFailingPredicate()
    step.execute()
    mock_add_failed.assert_called_once()

  @mock.patch('gcpdiag.runbook.op.prep_msg')
  @mock.patch('gcpdiag.runbook.gke.cluster_autoscaler.local_log_search')
  @mock.patch('gcpdiag.runbook.op.add_failed')
  @mock.patch('gcpdiag.runbook.op.get')
  @mock.patch('gcpdiag.queries.crm.get_project')
  def test_no_scale_up_in_backoff_logs(
    self, mock_crm, mock_get, mock_add_failed, mock_log_search, mock_prep_msg
  ):
    """CaNoScaleUpInBackoff detects MIGs in backoff state."""
    del mock_crm
    mock_prep_msg.side_effect = lambda x, **y: x
    mock_get.side_effect = lambda k, v=None: RUNBOOK_PARAMS.get(k, v)
    mock_log_search.return_value = [
      {
        'jsonPayload': {
          'noDecisionStatus': {
            'noScaleUp': {
              'skippedMigs': [
                {
                  'mig': {'name': 'gke-cluster-pool-1-mig', 'nodepool': 'pool-1'},
                  'reason': {
                    'messageId': 'no.scale.up.in.backoff',
                    'parameters': ['in backoff after failed scale-up'],
                  },
                }
              ]
            }
          }
        }
      }
    ]

    step = cluster_autoscaler.CaNoScaleUpInBackoff()
    step.execute()
    mock_add_failed.assert_called_once()
