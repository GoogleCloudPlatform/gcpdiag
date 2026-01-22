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
"""Test class for dataflow/JobPermissions"""

import datetime
import unittest
from unittest import mock

from gcpdiag import config
from gcpdiag.queries import apis_stub
from gcpdiag.runbook import dataflow, op, snapshot_test_base
from gcpdiag.runbook.crm import generalized_steps as crm_gs
from gcpdiag.runbook.dataflow import flags, job_permissions
from gcpdiag.runbook.iam import generalized_steps as iam_gs

DUMMY_PROJECT_ID = 'gcpdiag-dataflow1-aaaa'
DUMMY_GKE_PROJECT_ID = 'gcpdiag-gke1-aaaa'


class Test(snapshot_test_base.RulesSnapshotTestBase):
  rule_pkg = dataflow
  runbook_name = 'dataflow/job-permissions'
  config.init({'auto': True, 'interface': 'cli'})

  rule_parameters = [{
      'project_id': DUMMY_PROJECT_ID,
      'custom_flag': 'dataflow',
      'worker_service_account':
          ('dataflow-worker@gcpdiag-dataflow1-aaaa.iam.gserviceaccount.com'),
      'principal': 'user@xyz.com',
  }]


class MockMessage:
  """Mock messages for testing."""

  def get_msg(self, key, **kwargs):
    del kwargs
    return f'{key}'


class JobPermissionsStepTestBase(unittest.TestCase):
  """Base class for Job Permissions step tests."""

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
        flags.PRINCIPAL:
            'test-user@example.com',
        flags.WORKER_SERVICE_ACCOUNT:
            (f'dataflow-worker@{DUMMY_PROJECT_ID}.iam.gserviceaccount.com'),
        flags.CROSS_PROJECT_ID:
            None,
        flags.START_TIME:
            datetime.datetime(2025, 1, 1, tzinfo=datetime.timezone.utc),
        flags.END_TIME:
            datetime.datetime(2025, 1, 2, tzinfo=datetime.timezone.utc),
    }
    self.operator.parameters = self.params
    self.mock_logs_realtime_query = self.enterContext(
        mock.patch('gcpdiag.queries.logs.realtime_query'))


class JobPermissionsBuildTreeTest(unittest.TestCase):

  @mock.patch(
      'gcpdiag.runbook.dataflow.job_permissions.JobPermissions.add_step')
  @mock.patch(
      'gcpdiag.runbook.dataflow.job_permissions.JobPermissions.add_start')
  @mock.patch('gcpdiag.runbook.dataflow.job_permissions.JobPermissions.add_end')
  @mock.patch('gcpdiag.queries.apis.get_api', new=apis_stub.get_api_stub)
  @mock.patch('gcpdiag.runbook.op.get')
  def test_build_tree(
      self,
      mock_op_get,
      mock_add_end,
      mock_add_start,
      mock_add_step,
  ):
    mock_op_get.return_value = DUMMY_GKE_PROJECT_ID
    runbook = job_permissions.JobPermissions()
    runbook.build_tree()

    mock_add_start.assert_called_once()
    self.assertIsInstance(mock_add_start.call_args[0][0],
                          job_permissions.StartStep)

    self.assertEqual(mock_add_step.call_count, 4)
    steps_added = [call[1]['child'] for call in mock_add_step.call_args_list]
    self.assertTrue(
        any(
            isinstance(s, job_permissions.DataflowUserAccountPermissions)
            for s in steps_added))
    self.assertTrue(
        any(isinstance(s, iam_gs.IamPolicyCheck) for s in steps_added))
    self.assertTrue(
        any(
            isinstance(s,
                       job_permissions.DataflowWorkerServiceAccountPermissions)
            for s in steps_added))
    self.assertTrue(
        any(
            isinstance(s, job_permissions.DataflowResourcePermissions)
            for s in steps_added))

    mock_add_end.assert_called_once()
    self.assertIsInstance(mock_add_end.call_args[0][0],
                          job_permissions.DataflowPermissionsEnd)


class DataflowUserAccountPermissionsTest(JobPermissionsStepTestBase):

  def setUp(self):
    super().setUp()
    self.add_child_patch = self.enterContext(
        mock.patch(
            'gcpdiag.runbook.dataflow.job_permissions.DataflowUserAccountPermissions.add_child'
        ))

  def test_add_child_called(self):
    step = job_permissions.DataflowUserAccountPermissions()
    with op.operator_context(self.operator):
      self.operator.set_step(step)
      step.execute()
    self.add_child_patch.assert_called_once()
    self.assertIsInstance(self.add_child_patch.call_args[0][0],
                          iam_gs.IamPolicyCheck)


class DataflowWorkerServiceAccountPermissionsTest(JobPermissionsStepTestBase):

  def setUp(self):
    super().setUp()
    self.add_child_patch = self.enterContext(
        mock.patch('gcpdiag.runbook.dataflow.job_permissions.'
                   'DataflowWorkerServiceAccountPermissions.add_child'))

  @mock.patch('gcpdiag.queries.iam.is_service_account_existing',
              return_value=True)
  def test_sa_exists_same_project(self,
                                  unused_mock_is_service_account_existing):
    step = job_permissions.DataflowWorkerServiceAccountPermissions()
    with op.operator_context(self.operator):
      self.operator.set_step(step)
      step.execute()
    self.add_child_patch.assert_called_once()
    self.assertIsInstance(self.add_child_patch.call_args[1]['child'],
                          iam_gs.IamPolicyCheck)

  @mock.patch('gcpdiag.queries.iam.is_service_account_existing',
              return_value=False)
  def test_sa_does_not_exist(self, unused_mock_is_service_account_existing):
    self.params[flags.WORKER_SERVICE_ACCOUNT] = (
        f'non-existent@{DUMMY_PROJECT_ID}.iam.gserviceaccount.com')
    step = job_permissions.DataflowWorkerServiceAccountPermissions()
    with op.operator_context(self.operator):
      self.operator.set_step(step)
      step.execute()
    self.add_child_patch.assert_not_called()
    self.mock_interface.add_failed.assert_called_once()

  @mock.patch('gcpdiag.queries.iam.is_service_account_existing')
  def test_sa_exists_cross_project(self, mock_is_service_account_existing):
    self.params[flags.CROSS_PROJECT_ID] = 'gcpdiag-iam1-aaaa'
    self.params[flags.WORKER_SERVICE_ACCOUNT] = (
        'service-account-1@gcpdiag-iam1-aaaa.iam.gserviceaccount.com')
    mock_is_service_account_existing.side_effect = [False, True]
    step = job_permissions.DataflowWorkerServiceAccountPermissions()
    with op.operator_context(self.operator):
      self.operator.set_step(step)
      step.execute()
    # 1 org policy check + 1 sa perm check + 2 service agent perm checks
    self.assertEqual(self.add_child_patch.call_count, 4)
    self.assertIsInstance(self.add_child_patch.call_args_list[0][0][0],
                          crm_gs.OrgPolicyCheck)
    self.assertIsInstance(
        self.add_child_patch.call_args_list[1][1]['child'],
        iam_gs.IamPolicyCheck,
    )
    self.assertIsInstance(
        self.add_child_patch.call_args_list[2][1]['child'],
        iam_gs.IamPolicyCheck,
    )
    self.assertIsInstance(
        self.add_child_patch.call_args_list[3][1]['child'],
        iam_gs.IamPolicyCheck,
    )


class DataflowResourcePermissionsTest(JobPermissionsStepTestBase):

  def setUp(self):
    super().setUp()
    self.add_child_patch = self.enterContext(
        mock.patch(
            'gcpdiag.runbook.dataflow.job_permissions.DataflowResourcePermissions.add_child'
        ))

  def test_logs_found_same_project(self):
    self.mock_logs_realtime_query.return_value = [{'some': 'log'}]
    step = job_permissions.DataflowResourcePermissions()
    with op.operator_context(self.operator):
      self.operator.set_step(step)
      step.execute()
    self.mock_logs_realtime_query.assert_called_once()
    self.add_child_patch.assert_called_once()
    self.assertIsInstance(self.add_child_patch.call_args[0][0],
                          iam_gs.IamPolicyCheck)

  def test_logs_found_cross_project(self):
    self.params[flags.CROSS_PROJECT_ID] = 'cross-project'
    self.mock_logs_realtime_query.return_value = [{'some': 'log'}]
    step = job_permissions.DataflowResourcePermissions()
    with op.operator_context(self.operator):
      self.operator.set_step(step)
      step.execute()
    self.mock_logs_realtime_query.assert_called_once()
    self.add_child_patch.assert_called_once()
    added_step = self.add_child_patch.call_args[0][0]
    self.assertIsInstance(added_step, iam_gs.IamPolicyCheck)
    self.assertEqual(added_step.project, 'cross-project')

  def test_no_logs_found(self):
    self.mock_logs_realtime_query.return_value = []
    step = job_permissions.DataflowResourcePermissions()
    with op.operator_context(self.operator):
      self.operator.set_step(step)
      step.execute()
    self.mock_logs_realtime_query.assert_called_once()
    self.add_child_patch.assert_not_called()
    self.mock_interface.info.assert_called_with(
        'No Cloud Storage buckets related errors found in the logs',
        step_type='INFO',
    )


class DataflowPermissionsEndTest(JobPermissionsStepTestBase):

  def test_end_step(self):
    step = job_permissions.DataflowPermissionsEnd()
    with op.operator_context(self.operator):
      self.operator.set_step(step)
      step.execute()
    self.mock_interface.info.assert_called_once_with(
        'Dataflow Resources Permissions Checks Completed', step_type='INFO')


if __name__ == '__main__':
  unittest.main()
