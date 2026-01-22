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
"""Test class for dataproc/cluster-creation."""

import datetime
import unittest
from unittest import mock

from gcpdiag import config, utils
from gcpdiag.queries import apis_stub, crm, dataproc, gce
from gcpdiag.runbook import dataproc as dataproc_rb
from gcpdiag.runbook import op, snapshot_test_base
from gcpdiag.runbook.crm import generalized_steps as crm_gs
from gcpdiag.runbook.dataproc import cluster_creation, flags
from gcpdiag.runbook.iam import generalized_steps as iam_gs
from gcpdiag.runbook.logs import generalized_steps as logs_gs

DUMMY_PROJECT_ID = 'gcpdiag-dataproc1-aaaa'


class Test(snapshot_test_base.RulesSnapshotTestBase):
  rule_pkg = dataproc_rb
  runbook_name = 'dataproc/cluster-creation'
  config.init({'auto': True, 'interface': 'cli'})

  rule_parameters = [
      {
          'project_id': DUMMY_PROJECT_ID,
          'service_account':
              (f'saworker@{DUMMY_PROJECT_ID}.iam.gserviceaccount.com'),
          'region': 'us-central1',
          'dataproc_cluster_name': 'good',
          'start_time': '2024-06-18T01:00:00Z',
          'end_time': '2024-06-22T01:00:00Z',
      },
      {
          'project_id': DUMMY_PROJECT_ID,
          'service_account':
              (f'saworker@{DUMMY_PROJECT_ID}.iam.gserviceaccount.com'),
          'region': 'us-central1',
          'dataproc_cluster_name': 'good',
          'start_time': '2024-06-23T01:00:00Z',
          'end_time': '2024-06-24T01:00:00Z',
      },
      {
          'project_id': DUMMY_PROJECT_ID,
          'dataproc_cluster_name': 'test-deny-icmp',
          'region': 'us-central1',
          'start_time': '2024-06-18T01:00:00Z',
          'end_time': '2024-06-22T01:00:00Z',
      },
      {
          'project_id': 'gcpdiag-dataproc2-aaaa',
          'dataproc_cluster_name': 'cluster-quota-issues',
          'region': 'us-central1',
          'start_time': '2025-06-13T16:00:55Z',
          'end_time': '2025-06-13T17:00:55Z',
      },
      {
          'project_id': 'gcpdiag-dataproc3-aaaa',
          'dataproc_cluster_name': 'cluster-stockout-issues',
          'region': 'us-central1',
          'start_time': '2025-06-13T16:00:55Z',
          'end_time': '2025-06-13T17:00:55Z',
      },
  ]


class MockMessage:
  """Mock messages for testing."""

  def get_msg(self, key, **kwargs):
    del kwargs
    return f'{key}'


class ClusterCreationTest(unittest.TestCase):

  def test_legacy_parameter_handler(self):
    runbook = cluster_creation.ClusterCreation()
    parameters = {
        'cluster_name': 'test-cluster',
        'network': 'test-network',
        'project_id': 'test-project',
        'region': 'us-central1',
    }
    runbook.legacy_parameter_handler(parameters)
    self.assertNotIn('cluster_name', parameters)
    self.assertNotIn('network', parameters)
    self.assertIn('dataproc_cluster_name', parameters)
    self.assertIn('dataproc_network', parameters)
    self.assertEqual(parameters['dataproc_cluster_name'], 'test-cluster')
    self.assertEqual(parameters['dataproc_network'], 'test-network')


class ClusterCreationBuildTreeTest(unittest.TestCase):

  @mock.patch(
      'gcpdiag.runbook.dataproc.cluster_creation.ClusterCreation.add_step')
  @mock.patch(
      'gcpdiag.runbook.dataproc.cluster_creation.ClusterCreation.add_start')
  @mock.patch(
      'gcpdiag.runbook.dataproc.cluster_creation.ClusterCreation.add_end')
  @mock.patch('gcpdiag.runbook.op.get')
  def test_build_tree(self, mock_op_get, mock_add_end, mock_add_start,
                      mock_add_step):
    mock_op_get.return_value = 'test_value'
    runbook = cluster_creation.ClusterCreation()
    runbook.build_tree()
    mock_add_start.assert_called_once()
    self.assertIsInstance(mock_add_start.call_args[0][0],
                          cluster_creation.ClusterCreationStart)
    mock_add_step.assert_called_once()
    self.assertIsInstance(
        mock_add_step.call_args[1]['child'],
        cluster_creation.ClusterDetailsDependencyGateway,
    )
    mock_add_end.assert_called_once()
    self.assertIsInstance(mock_add_end.call_args[0][0],
                          cluster_creation.ClusterCreationEnd)


class ClusterCreationStepTestBase(unittest.TestCase):
  """Base class for Cluster Creation step tests."""

  def setUp(self):
    super().setUp()
    # 1. Patch get_api with the stub.
    self.enterContext(
        mock.patch('gcpdiag.queries.apis.get_api', new=apis_stub.get_api_stub))
    # 2. Create a mock interface to capture outputs
    self.mock_interface = mock.create_autospec(op.InteractionInterface,
                                               instance=True)
    self.mock_interface.rm = mock.Mock()
    # 3. Instantiate a real Operator
    self.operator = op.Operator(self.mock_interface)
    self.operator.run_id = 'test-run'
    self.operator.messages = MockMessage()
    # 4. Define standard parameters.
    self.params = {
        flags.PROJECT_ID:
            DUMMY_PROJECT_ID,
        flags.REGION:
            'us-central1',
        flags.DATAPROC_CLUSTER_NAME:
            'test-cluster',
        flags.SERVICE_ACCOUNT:
            None,
        flags.DATAPROC_NETWORK:
            None,
        flags.ZONE:
            None,
        flags.INTERNAL_IP_ONLY:
            None,
        flags.SUBNETWORK:
            None,
        flags.START_TIME:
            datetime.datetime(2025, 1, 1, tzinfo=datetime.timezone.utc),
        flags.END_TIME:
            datetime.datetime(2025, 1, 2, tzinfo=datetime.timezone.utc),
        flags.CROSS_PROJECT_ID:
            None,
        flags.HOST_VPC_PROJECT_ID:
            None,
    }
    self.operator.parameters = self.params
    self.mock_op_put = self.enterContext(mock.patch('gcpdiag.runbook.op.put'))
    self.mock_op_put.side_effect = self.params.__setitem__
    self.mock_dataproc_get_cluster = self.enterContext(
        mock.patch('gcpdiag.queries.dataproc.get_cluster',
                   wraps=dataproc.get_cluster))
    self.mock_crm_get_project = self.enterContext(
        mock.patch('gcpdiag.queries.crm.get_project', wraps=crm.get_project))
    self.mock_gce_get_instance = self.enterContext(
        mock.patch('gcpdiag.queries.gce.get_instance'))
    self.mock_iam_is_service_account_existing = self.enterContext(
        mock.patch('gcpdiag.queries.iam.is_service_account_existing'))
    self.mock_logs_realtime_query = self.enterContext(
        mock.patch('gcpdiag.queries.logs.realtime_query'))
    self.mock_network_get_network_from_url = self.enterContext(
        mock.patch('gcpdiag.queries.network.get_network_from_url'))
    self.mock_network_get_subnetwork_from_url = self.enterContext(
        mock.patch('gcpdiag.queries.network.get_subnetwork_from_url'))
    self.mock_networkmanagement_run_connectivity_test = self.enterContext(
        mock.patch('gcpdiag.queries.networkmanagement.run_connectivity_test'))

    self.mock_cluster = mock.Mock(spec=dataproc.Cluster)
    self.mock_cluster.name = 'test-cluster'
    self.mock_cluster.status = 'ERROR'
    self.mock_cluster.is_stackdriver_logging_enabled = True
    self.mock_cluster.vm_service_account_email = 'test-sa@domain.com'
    self.mock_cluster.gce_network_uri = 'test-network'
    self.mock_cluster.zone = 'us-central1-a'
    self.mock_cluster.is_gce_cluster = True
    self.mock_cluster.is_single_node_cluster = False
    self.mock_cluster.is_ha_cluster = False
    self.mock_cluster.is_internal_ip_only = False
    self.mock_cluster.gce_subnetwork_uri = 'test-subnetwork'


class ClusterCreationStartTest(ClusterCreationStepTestBase):

  def test_cluster_in_error_state(self):
    self.params[flags.DATAPROC_CLUSTER_NAME] = 'test-deny-icmp'
    step = cluster_creation.ClusterCreationStart()
    with op.operator_context(self.operator):
      self.operator.set_step(step)
      step.execute()
    self.mock_op_put.assert_any_call('cluster_exists', True)
    self.mock_dataproc_get_cluster.assert_called_once()
    self.mock_interface.add_skipped.assert_not_called()

  def test_cluster_not_in_error_state(self):
    self.params[flags.DATAPROC_CLUSTER_NAME] = 'good'
    step = cluster_creation.ClusterCreationStart()
    with op.operator_context(self.operator):
      self.operator.set_step(step)
      step.execute()
    self.mock_op_put.assert_any_call('cluster_exists', True)
    self.mock_interface.add_skipped.assert_called_once()

  def test_cluster_api_error(self):
    self.mock_dataproc_get_cluster.side_effect = utils.GcpApiError('api error')
    step = cluster_creation.ClusterCreationStart()
    with op.operator_context(self.operator):
      self.operator.set_step(step)
      step.execute()
    self.mock_interface.add_skipped.assert_called_once()

  def test_cluster_not_found(self):
    self.params[flags.DATAPROC_CLUSTER_NAME] = 'non-existent'
    self.mock_dataproc_get_cluster.return_value = None
    step = cluster_creation.ClusterCreationStart()
    with op.operator_context(self.operator):
      self.operator.set_step(step)
      step.execute()
    self.mock_op_put.assert_any_call('cluster_exists', False)

  def test_cluster_in_error_state_stackdriver_disabled(self):
    self.mock_cluster.status = 'ERROR'
    self.mock_cluster.is_stackdriver_logging_enabled = False
    self.mock_dataproc_get_cluster.return_value = self.mock_cluster
    step = cluster_creation.ClusterCreationStart()
    with op.operator_context(self.operator):
      self.operator.set_step(step)
      step.execute()
    self.mock_op_put.assert_any_call('cluster_exists', True)
    self.mock_op_put.assert_any_call(flags.STACKDRIVER, False)
    self.mock_dataproc_get_cluster.assert_called_once()
    self.mock_interface.add_skipped.assert_not_called()


class ClusterCreationStockoutTest(ClusterCreationStepTestBase):

  def setUp(self):
    super().setUp()
    self.add_child_patch = self.enterContext(
        mock.patch(
            'gcpdiag.runbook.dataproc.cluster_creation.ClusterCreationStockout.add_child'
        ))

  def test_add_child_called(self):
    step = cluster_creation.ClusterCreationStockout()
    with op.operator_context(self.operator):
      self.operator.set_step(step)
      step.execute()
    self.add_child_patch.assert_called_once()
    self.assertIsInstance(self.add_child_patch.call_args[1]['child'],
                          logs_gs.CheckIssueLogEntry)


class ClusterCreationQuotaTest(ClusterCreationStepTestBase):

  def setUp(self):
    super().setUp()
    self.add_child_patch = self.enterContext(
        mock.patch(
            'gcpdiag.runbook.dataproc.cluster_creation.ClusterCreationQuota.add_child'
        ))

  def test_add_child_called(self):
    step = cluster_creation.ClusterCreationQuota()
    with op.operator_context(self.operator):
      self.operator.set_step(step)
      step.execute()
    self.add_child_patch.assert_called_once()
    self.assertIsInstance(self.add_child_patch.call_args[1]['child'],
                          logs_gs.CheckIssueLogEntry)


class ClusterDetailsDependencyGatewayTest(ClusterCreationStepTestBase):

  def setUp(self):
    super().setUp()
    self.add_child_patch = self.enterContext(
        mock.patch(
            'gcpdiag.runbook.dataproc.cluster_creation.ClusterDetailsDependencyGateway.add_child'
        ))

  def test_cluster_exists(self):
    self.params['cluster_exists'] = True
    step = cluster_creation.ClusterDetailsDependencyGateway()
    with op.operator_context(self.operator):
      self.operator.set_step(step)
      step.execute()
    steps_added = [call[0][0] for call in self.add_child_patch.call_args_list]
    self.assertTrue(
        any(
            isinstance(s, cluster_creation.CheckInitScriptFailure)
            for s in steps_added))
    self.assertTrue(
        any(
            isinstance(s, cluster_creation.CheckClusterNetwork)
            for s in steps_added))
    self.assertTrue(
        any(
            isinstance(s, cluster_creation.InternalIpGateway)
            for s in steps_added))
    self.assertTrue(
        any(
            isinstance(s, cluster_creation.ServiceAccountExists)
            for s in steps_added))
    self.assertTrue(
        any(
            isinstance(s, cluster_creation.CheckSharedVPCRoles)
            for s in steps_added))

  def test_cluster_does_not_exist(self):
    self.params['cluster_exists'] = False
    step = cluster_creation.ClusterDetailsDependencyGateway()
    with op.operator_context(self.operator):
      self.operator.set_step(step)
      step.execute()
    steps_added = [call[0][0] for call in self.add_child_patch.call_args_list]
    self.assertTrue(
        any(
            isinstance(s, cluster_creation.ClusterCreationQuota)
            for s in steps_added))
    self.assertTrue(
        any(
            isinstance(s, cluster_creation.ClusterCreationStockout)
            for s in steps_added))


class CheckClusterNetworkTest(ClusterCreationStepTestBase):

  def setUp(self):
    super().setUp()
    self.mock_instance = mock.Mock(spec=gce.Instance)
    self.mock_instance.get_network_ip_for_instance_interface.return_value = (
        '10.0.0.1/32')
    self.mock_gce_get_instance.return_value = self.mock_instance
    self.mock_networkmanagement_run_connectivity_test.return_value = {
        'reachabilityDetails': {
            'result': 'REACHABLE',
            'traces': []
        }
    }

  def test_cluster_none(self):
    self.mock_dataproc_get_cluster.return_value = None
    step = cluster_creation.CheckClusterNetwork()
    with op.operator_context(self.operator):
      self.operator.set_step(step)
      step.execute()
    self.mock_interface.add_uncertain.assert_called_once()

  def test_no_zone(self):
    self.mock_cluster.zone = None
    self.params[flags.ZONE] = None
    self.mock_dataproc_get_cluster.return_value = self.mock_cluster
    step = cluster_creation.CheckClusterNetwork()
    with op.operator_context(self.operator):
      self.operator.set_step(step)
      step.execute()
    self.mock_interface.add_skipped.assert_called_once()

  def test_dpgke_cluster(self):
    self.mock_cluster.is_gce_cluster = False
    self.mock_dataproc_get_cluster.return_value = self.mock_cluster
    step = cluster_creation.CheckClusterNetwork()
    with op.operator_context(self.operator):
      self.operator.set_step(step)
      step.execute()
    self.mock_interface.add_skipped.assert_called_once()

  def test_single_node_cluster(self):
    self.mock_cluster.is_single_node_cluster = True
    self.mock_dataproc_get_cluster.return_value = self.mock_cluster
    step = cluster_creation.CheckClusterNetwork()
    with op.operator_context(self.operator):
      self.operator.set_step(step)
      step.execute()
    self.mock_interface.add_skipped.assert_called_once()

  def test_connectivity_ok(self):
    self.mock_dataproc_get_cluster.return_value = self.mock_cluster
    step = cluster_creation.CheckClusterNetwork()
    with op.operator_context(self.operator):
      self.operator.set_step(step)
      step.execute()
    self.assertEqual(
        self.mock_networkmanagement_run_connectivity_test.call_count, 3)
    self.mock_interface.add_ok.assert_called_once()

  def test_connectivity_failed_icmp(self):
    self.mock_networkmanagement_run_connectivity_test.side_effect = [
        {
            'reachabilityDetails': {
                'result': 'UNREACHABLE',
                'traces': [{
                    'steps': [{
                        'foo': 'bar'
                    }],
                    'endpointInfo': {}
                }],
            }
        },
        {
            'reachabilityDetails': {
                'result': 'REACHABLE',
                'traces': []
            }
        },
        {
            'reachabilityDetails': {
                'result': 'REACHABLE',
                'traces': []
            }
        },
    ]
    self.mock_dataproc_get_cluster.return_value = self.mock_cluster
    step = cluster_creation.CheckClusterNetwork()
    with op.operator_context(self.operator):
      self.operator.set_step(step)
      step.execute()
    self.mock_interface.add_failed.assert_called_once()

  def test_connectivity_failed_tcp(self):
    self.mock_networkmanagement_run_connectivity_test.side_effect = [
        {
            'reachabilityDetails': {
                'result': 'REACHABLE',
                'traces': []
            }
        },
        {
            'reachabilityDetails': {
                'result': 'UNREACHABLE',
                'traces': [{
                    'steps': [{
                        'foo': 'bar'
                    }],
                    'endpointInfo': {}
                }],
            }
        },
        {
            'reachabilityDetails': {
                'result': 'REACHABLE',
                'traces': []
            }
        },
    ]
    self.mock_dataproc_get_cluster.return_value = self.mock_cluster
    step = cluster_creation.CheckClusterNetwork()
    with op.operator_context(self.operator):
      self.operator.set_step(step)
      step.execute()
    self.mock_interface.add_failed.assert_called_once()

  def test_connectivity_failed_udp(self):
    self.mock_networkmanagement_run_connectivity_test.side_effect = [
        {
            'reachabilityDetails': {
                'result': 'REACHABLE',
                'traces': []
            }
        },
        {
            'reachabilityDetails': {
                'result': 'REACHABLE',
                'traces': []
            }
        },
        {
            'reachabilityDetails': {
                'result': 'UNREACHABLE',
                'traces': [{
                    'steps': [{
                        'foo': 'bar'
                    }],
                    'endpointInfo': {}
                }],
            }
        },
    ]
    self.mock_dataproc_get_cluster.return_value = self.mock_cluster
    step = cluster_creation.CheckClusterNetwork()
    with op.operator_context(self.operator):
      self.operator.set_step(step)
      step.execute()
    self.mock_interface.add_failed.assert_called_once()

  def test_ha_cluster_connectivity_ok(self):
    self.mock_cluster.is_ha_cluster = True
    self.mock_dataproc_get_cluster.return_value = self.mock_cluster
    step = cluster_creation.CheckClusterNetwork()
    with op.operator_context(self.operator):
      self.operator.set_step(step)
      step.execute()
    self.mock_gce_get_instance.assert_any_call(
        project_id=DUMMY_PROJECT_ID,
        zone='us-central1-a',
        instance_name='test-cluster-m-0',
    )
    self.assertEqual(
        self.mock_networkmanagement_run_connectivity_test.call_count, 3)
    self.mock_interface.add_ok.assert_called_once()


class InternalIpGatewayTest(ClusterCreationStepTestBase):

  def setUp(self):
    super().setUp()
    self.add_child_patch = self.enterContext(
        mock.patch(
            'gcpdiag.runbook.dataproc.cluster_creation.InternalIpGateway.add_child'
        ))

  def test_cluster_none_no_flag(self):
    self.mock_dataproc_get_cluster.return_value = None
    self.params[flags.INTERNAL_IP_ONLY] = None
    step = cluster_creation.InternalIpGateway()
    with op.operator_context(self.operator):
      self.operator.set_step(step)
      step.execute()
    self.mock_interface.add_skipped.assert_called_once()

  def test_cluster_none_no_subnet(self):
    self.mock_dataproc_get_cluster.return_value = None
    self.params[flags.INTERNAL_IP_ONLY] = True
    self.params[flags.SUBNETWORK] = None
    step = cluster_creation.InternalIpGateway()
    with op.operator_context(self.operator):
      self.operator.set_step(step)
      step.execute()
    self.mock_interface.add_skipped.assert_called_once()

  def test_internal_ip_only_true(self):
    self.mock_cluster.is_internal_ip_only = True
    self.mock_dataproc_get_cluster.return_value = self.mock_cluster
    step = cluster_creation.InternalIpGateway()
    with op.operator_context(self.operator):
      self.operator.set_step(step)
      step.execute()
    self.add_child_patch.assert_called_once()
    self.assertIsInstance(
        self.add_child_patch.call_args[1]['child'],
        cluster_creation.CheckPrivateGoogleAccess,
    )

  def test_internal_ip_only_false(self):
    self.mock_cluster.is_internal_ip_only = False
    self.mock_dataproc_get_cluster.return_value = self.mock_cluster
    step = cluster_creation.InternalIpGateway()
    with op.operator_context(self.operator):
      self.operator.set_step(step)
      step.execute()
    self.add_child_patch.assert_not_called()
    self.assertEqual(self.mock_interface.add_ok.call_count, 2)


class CheckPrivateGoogleAccessTest(ClusterCreationStepTestBase):

  def test_pga_enabled(self):
    self.mock_dataproc_get_cluster.return_value = self.mock_cluster
    mock_subnet = mock.Mock()
    mock_subnet.is_private_ip_google_access.return_value = True
    self.mock_network_get_subnetwork_from_url.return_value = mock_subnet
    step = cluster_creation.CheckPrivateGoogleAccess()
    with op.operator_context(self.operator):
      self.operator.set_step(step)
      step.execute()
    self.mock_interface.add_ok.assert_called_once()

  def test_pga_disabled(self):
    self.mock_dataproc_get_cluster.return_value = self.mock_cluster
    mock_subnet = mock.Mock()
    mock_subnet.is_private_ip_google_access.return_value = False
    self.mock_network_get_subnetwork_from_url.return_value = mock_subnet
    step = cluster_creation.CheckPrivateGoogleAccess()
    with op.operator_context(self.operator):
      self.operator.set_step(step)
      step.execute()
    self.mock_interface.add_failed.assert_called_once()


class ServiceAccountExistsTest(ClusterCreationStepTestBase):

  def setUp(self):
    super().setUp()
    self.params[flags.SERVICE_ACCOUNT] = 'test-sa@example.com'
    self.add_child_patch = self.enterContext(
        mock.patch(
            'gcpdiag.runbook.dataproc.cluster_creation.ServiceAccountExists.add_child'
        ))

  def test_no_sa_email(self):
    self.params[flags.SERVICE_ACCOUNT] = None
    step = cluster_creation.ServiceAccountExists()
    with op.operator_context(self.operator):
      self.operator.set_step(step)
      step.execute()
    self.mock_interface.add_skipped.assert_called_once()

  def test_sa_exists_same_project(self):
    self.params[flags.PROJECT_ID] = 'gcpdiag-iam1-aaaa'
    self.params[flags.SERVICE_ACCOUNT] = (
        'service-account-1@gcpdiag-iam1-aaaa.iam.gserviceaccount.com')
    self.mock_iam_is_service_account_existing.return_value = True
    step = cluster_creation.ServiceAccountExists()
    with op.operator_context(self.operator):
      self.operator.set_step(step)
      step.execute()
    self.add_child_patch.assert_called_once()
    self.assertIsInstance(self.add_child_patch.call_args[1]['child'],
                          iam_gs.IamPolicyCheck)

  def test_sa_exists_cross_project(self):
    self.params[flags.PROJECT_ID] = 'gcpdiag-dataproc1-aaaa'
    self.params[flags.CROSS_PROJECT_ID] = 'gcpdiag-iam1-aaaa'
    self.params[flags.SERVICE_ACCOUNT] = (
        'service-account-1@gcpdiag-iam1-aaaa.iam.gserviceaccount.com')
    self.mock_iam_is_service_account_existing.side_effect = [False, True]
    step = cluster_creation.ServiceAccountExists()
    with op.operator_context(self.operator):
      self.operator.set_step(step)
      step.execute()
    steps_added = []
    for call in self.add_child_patch.call_args_list:
      if call[0]:
        steps_added.append(call[0][0])
      elif call[1] and 'child' in call[1]:
        steps_added.append(call[1]['child'])
    self.assertTrue(
        any(isinstance(s, crm_gs.OrgPolicyCheck) for s in steps_added))
    self.assertEqual(
        sum(1 for s in steps_added if isinstance(s, iam_gs.IamPolicyCheck)), 3)

  def test_sa_not_exists_cross_project(self):
    self.params[flags.CROSS_PROJECT_ID] = 'gcpdiag-iam1-aaaa'
    self.params[flags.SERVICE_ACCOUNT] = (
        'non-existent@gcpdiag-iam1-aaaa.iam.gserviceaccount.com')
    self.mock_iam_is_service_account_existing.return_value = False
    step = cluster_creation.ServiceAccountExists()
    with op.operator_context(self.operator):
      self.operator.set_step(step)
      step.execute()
    self.mock_interface.add_failed.assert_called_once()

  def test_sa_not_exists_no_cross_project(self):
    self.params[flags.SERVICE_ACCOUNT] = (
        'non-existent@gcpdiag-iam1-aaaa.iam.gserviceaccount.com')
    self.mock_iam_is_service_account_existing.return_value = False
    step = cluster_creation.ServiceAccountExists()
    with op.operator_context(self.operator):
      self.operator.set_step(step)
      step.execute()
    self.mock_interface.add_uncertain.assert_called_once()


class CheckSharedVPCRolesTest(ClusterCreationStepTestBase):

  def setUp(self):
    super().setUp()
    self.add_child_patch = self.enterContext(
        mock.patch(
            'gcpdiag.runbook.dataproc.cluster_creation.CheckSharedVPCRoles.add_child'
        ))

  def test_shared_vpc(self):
    self.params[flags.HOST_VPC_PROJECT_ID] = 'host-project'
    self.params[flags.PROJECT_ID] = 'service-project'
    self.mock_crm_get_project.return_value = mock.Mock(number=123)
    step = cluster_creation.CheckSharedVPCRoles()
    with op.operator_context(self.operator):
      self.operator.set_step(step)
      step.execute()
    steps_added = [
        call[1]['child'] for call in self.add_child_patch.call_args_list
    ]
    self.assertEqual(
        sum(1 for s in steps_added if isinstance(s, iam_gs.IamPolicyCheck)), 2)

  def test_no_shared_vpc(self):
    self.params[flags.HOST_VPC_PROJECT_ID] = DUMMY_PROJECT_ID
    self.params[flags.PROJECT_ID] = DUMMY_PROJECT_ID
    step = cluster_creation.CheckSharedVPCRoles()
    with op.operator_context(self.operator):
      self.operator.set_step(step)
      step.execute()
    self.mock_interface.add_skipped.assert_called_once()


class CheckInitScriptFailureTest(ClusterCreationStepTestBase):

  def test_failure_logs_found(self):
    self.mock_logs_realtime_query.return_value = [{'some': 'log'}]
    step = cluster_creation.CheckInitScriptFailure()
    with op.operator_context(self.operator):
      self.operator.set_step(step)
      step.execute()
    self.mock_interface.add_failed.assert_called_once()

  def test_no_failure_logs(self):
    self.mock_logs_realtime_query.return_value = []
    step = cluster_creation.CheckInitScriptFailure()
    with op.operator_context(self.operator):
      self.operator.set_step(step)
      step.execute()
    self.mock_interface.add_ok.assert_called_once()


class ClusterCreationEndTest(ClusterCreationStepTestBase):

  def test_cluster_exists(self):
    self.params['cluster_exists'] = True
    step = cluster_creation.ClusterCreationEnd()
    with op.operator_context(self.operator):
      self.operator.set_step(step)
      step.execute()
    self.mock_interface.info.assert_called_once()
    self.assertIn(
        'Please visit all the FAIL steps',
        self.mock_interface.info.call_args[0][0],
    )

  def test_cluster_does_not_exist(self):
    self.params['cluster_exists'] = False
    step = cluster_creation.ClusterCreationEnd()
    with op.operator_context(self.operator):
      self.operator.set_step(step)
      step.execute()
    self.mock_interface.info.assert_called_once()
    self.assertIn('Some steps were skipped',
                  self.mock_interface.info.call_args[0][0])


if __name__ == '__main__':
  unittest.main()
