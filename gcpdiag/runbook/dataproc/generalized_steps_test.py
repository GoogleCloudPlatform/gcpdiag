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
"""Test class for dataproc.generalized_steps."""

import datetime
import unittest
from unittest import mock

from gcpdiag.queries import apis_stub, crm, dataproc, gce
from gcpdiag.runbook import op
from gcpdiag.runbook.dataproc import flags, generalized_steps

DUMMY_PROJECT_ID = 'gcpdiag-dataproc1-aaaa'


class MockMessage:
  """Mock messages for testing."""

  def get_msg(self, key, **kwargs):
    del kwargs
    return f'{key}'


class GeneralizedStepsTestBase(unittest.TestCase):
  """Base class for Dataproc generalized step tests."""

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
        flags.JOB_ID:
            'test-job',
        flags.DATAPROC_JOB_ID:
            'test-dataproc-job',
        flags.JOB_EXIST:
            'true',
        flags.JOB_OLDER_THAN_30_DAYS:
            False,
        flags.START_TIME:
            datetime.datetime(2025, 1, 1, tzinfo=datetime.timezone.utc),
        flags.END_TIME:
            datetime.datetime(2025, 1, 2, tzinfo=datetime.timezone.utc),
        flags.ZONE:
            None,
    }
    self.operator.parameters = self.params
    self.mock_op_put = self.enterContext(mock.patch('gcpdiag.runbook.op.put'))
    self.mock_op_put.side_effect = self.params.__setitem__

    self.mock_crm_get_project = self.enterContext(
        mock.patch('gcpdiag.queries.crm.get_project'))
    self.mock_dataproc_get_job_by_jobid = self.enterContext(
        mock.patch('gcpdiag.queries.dataproc.get_job_by_jobid'))
    self.mock_logs_realtime_query = self.enterContext(
        mock.patch('gcpdiag.queries.logs.realtime_query'))
    self.mock_dataproc_get_cluster = self.enterContext(
        mock.patch('gcpdiag.queries.dataproc.get_cluster'))
    self.mock_gce_get_instance = self.enterContext(
        mock.patch('gcpdiag.queries.gce.get_instance'))
    self.mock_networkmanagement_run_connectivity_test = self.enterContext(
        mock.patch('gcpdiag.queries.networkmanagement.run_connectivity_test'))

    self.mock_project = mock.Mock(spec=crm.Project)
    self.mock_project.id = 'test-project'
    self.mock_crm_get_project.return_value = self.mock_project

    self.mock_job = mock.Mock(spec=dataproc.Job)
    self.mock_job.cluster_name = 'test-cluster'
    self.mock_job.cluster_uuid = 'test-uuid'
    self.mock_dataproc_get_job_by_jobid.return_value = self.mock_job

    self.mock_cluster = mock.Mock(spec=dataproc.Cluster)
    self.mock_cluster.name = 'test-cluster'
    self.mock_cluster.zone = 'us-central1-a'
    self.mock_cluster.is_gce_cluster = True
    self.mock_cluster.is_single_node_cluster = False
    self.mock_cluster.is_ha_cluster = False
    self.mock_cluster.gce_network_uri = 'test-network'
    self.mock_dataproc_get_cluster.return_value = self.mock_cluster


class CheckLogsExistTest(GeneralizedStepsTestBase):

  def test_job_does_not_exist(self):
    self.params[flags.JOB_EXIST] = 'false'
    step = generalized_steps.CheckLogsExist(log_message='test message')
    with op.operator_context(self.operator):
      self.operator.set_step(step)
      step.execute()
    self.mock_interface.add_skipped.assert_called_once()

  def test_job_too_old(self):
    self.params[flags.JOB_OLDER_THAN_30_DAYS] = True
    step = generalized_steps.CheckLogsExist(log_message='test message')
    with op.operator_context(self.operator):
      self.operator.set_step(step)
      step.execute()
    self.mock_interface.add_skipped.assert_called_once()

  def test_logs_found_no_cluster_details(self):
    self.mock_logs_realtime_query.return_value = [{'some': 'log'}]
    step = generalized_steps.CheckLogsExist(log_message='test message')
    with op.operator_context(self.operator):
      self.operator.set_step(step)
      step.execute()
    self.mock_dataproc_get_job_by_jobid.assert_called_once()
    self.mock_logs_realtime_query.assert_called_once()
    self.mock_interface.add_failed.assert_called_once()

  def test_logs_not_found_no_cluster_details(self):
    self.mock_logs_realtime_query.return_value = []
    step = generalized_steps.CheckLogsExist(log_message='test message')
    with op.operator_context(self.operator):
      self.operator.set_step(step)
      step.execute()
    self.mock_dataproc_get_job_by_jobid.assert_called_once()
    self.mock_logs_realtime_query.assert_called_once()
    self.mock_interface.add_ok.assert_called_once()

  def test_logs_found_with_cluster_details(self):
    self.mock_logs_realtime_query.return_value = [{'some': 'log'}]
    step = generalized_steps.CheckLogsExist(
        log_message='test message',
        cluster_name='test-cluster',
        cluster_uuid='test-uuid',
    )
    with op.operator_context(self.operator):
      self.operator.set_step(step)
      step.execute()
    self.mock_dataproc_get_job_by_jobid.assert_not_called()
    self.mock_logs_realtime_query.assert_called_once()
    self.mock_interface.add_failed.assert_called_once()

  def test_logs_found_with_project_id(self):
    self.mock_logs_realtime_query.return_value = [{'some': 'log'}]
    step = generalized_steps.CheckLogsExist(
        log_message='test message',
        cluster_name='test-cluster',
        cluster_uuid='test-uuid',
        project_id='step-project',
    )
    with op.operator_context(self.operator):
      self.operator.set_step(step)
      step.execute()
    self.mock_crm_get_project.assert_called_with('step-project')
    self.mock_logs_realtime_query.assert_called_once()
    self.mock_interface.add_failed.assert_called_once()


class CheckClusterNetworkConnectivityTest(GeneralizedStepsTestBase):

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
    step = generalized_steps.CheckClusterNetworkConnectivity()
    with op.operator_context(self.operator):
      self.operator.set_step(step)
      step.execute()
    self.mock_interface.add_uncertain.assert_called_once()

  def test_no_zone(self):
    self.mock_cluster.zone = None
    step = generalized_steps.CheckClusterNetworkConnectivity()
    with op.operator_context(self.operator):
      self.operator.set_step(step)
      step.execute()
    self.mock_interface.add_skipped.assert_called_once()

  def test_dpgke_cluster(self):
    self.mock_cluster.is_gce_cluster = False
    step = generalized_steps.CheckClusterNetworkConnectivity()
    with op.operator_context(self.operator):
      self.operator.set_step(step)
      step.execute()
    self.mock_interface.add_skipped.assert_called_once()

  def test_single_node_cluster(self):
    self.mock_cluster.is_single_node_cluster = True
    step = generalized_steps.CheckClusterNetworkConnectivity()
    with op.operator_context(self.operator):
      self.operator.set_step(step)
      step.execute()
    self.mock_interface.add_skipped.assert_called_once()

  def test_connectivity_ok(self):
    step = generalized_steps.CheckClusterNetworkConnectivity()
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
    step = generalized_steps.CheckClusterNetworkConnectivity()
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
    step = generalized_steps.CheckClusterNetworkConnectivity()
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
    step = generalized_steps.CheckClusterNetworkConnectivity()
    with op.operator_context(self.operator):
      self.operator.set_step(step)
      step.execute()
    self.mock_interface.add_failed.assert_called_once()

  def test_ha_cluster_connectivity_ok(self):
    self.mock_cluster.is_ha_cluster = True
    step = generalized_steps.CheckClusterNetworkConnectivity()
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

  def test_step_with_cluster_name_and_project_id(self):
    step = generalized_steps.CheckClusterNetworkConnectivity(
        cluster_name='step-cluster', project_id='step-project')
    with op.operator_context(self.operator):
      self.operator.set_step(step)
      step.execute()
    self.mock_dataproc_get_cluster.assert_called_with(
        cluster_name='step-cluster',
        region='us-central1',
        project='step-project',
    )
    self.assertEqual(
        self.mock_networkmanagement_run_connectivity_test.call_count, 3)
    self.mock_interface.add_ok.assert_called_once()


if __name__ == '__main__':
  unittest.main()
