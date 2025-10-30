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
"""Snapshot testing and unittest """

from unittest import mock

from dateutil import parser

from gcpdiag import config
from gcpdiag.queries import crm
from gcpdiag.runbook import gce, snapshot_test_base
from gcpdiag.runbook.gce import constants, flags, vm_termination

from .generalized_steps_test import GceStepTestBase


def make_operation(op_type,
                   start_time='2025-03-18T12:00:00Z',
                   progress=100,
                   status_message='test',
                   user='test@example.com',
                   name='test-op'):
  return {
      'operationType': op_type,
      'startTime': start_time,
      'progress': progress,
      'statusMessage': status_message,
      'user': user,
      'name': name
  }


class TerminationOperationTypeTest(GceStepTestBase):
  """Test TerminationOperationType Gateway."""

  def setUp(self):
    super().setUp()
    self.mock_project = mock.Mock(spec=crm.Project)
    self.mock_project.number = 12345
    self.crm_get_project_patch = self.enterContext(
        mock.patch('gcpdiag.queries.crm.get_project',
                   return_value=self.mock_project))
    self.gce_get_ops_patch = self.enterContext(
        mock.patch('gcpdiag.queries.gce.get_global_operations'))

    self.start_time = parser.parse('2025-03-18T00:00:00Z')
    self.end_time = parser.parse('2025-03-19T00:00:00Z')
    self.mock_op_get.side_effect = lambda key, d=None: {
        flags.PROJECT_ID: 'test-project',
        flags.INSTANCE_ID: '111222333',
        flags.INSTANCE_NAME: 'test-instance',
        flags.ZONE: 'us-central1-a',
        flags.START_TIME: self.start_time,
        flags.END_TIME: self.end_time,
    }.get(key, d)

  def test_host_error_operation(self):
    self.gce_get_ops_patch.return_value = [
        make_operation(constants.HOST_ERROR_METHOD)
    ]
    step = vm_termination.TerminationOperationType()
    with mock.patch.object(step, 'add_child') as mock_add_child:
      step.execute()
      mock_add_child.assert_called_once()
      self.assertIsInstance(mock_add_child.call_args[0][0],
                            vm_termination.HostError)

  def test_stop_operation(self):
    self.gce_get_ops_patch.return_value = [make_operation('stop')]
    step = vm_termination.TerminationOperationType()
    with mock.patch.object(step, 'add_child') as mock_add_child:
      step.execute()
      mock_add_child.assert_called_once()
      self.assertIsInstance(mock_add_child.call_args[0][0],
                            vm_termination.StopOperationGateway)

  def test_preempted_operation(self):
    self.gce_get_ops_patch.return_value = [
        make_operation(constants.INSTANCE_PREMPTION_METHOD)
    ]
    step = vm_termination.TerminationOperationType()
    with mock.patch.object(step, 'add_child') as mock_add_child:
      step.execute()
      mock_add_child.assert_called_once()
      self.assertIsInstance(mock_add_child.call_args[0][0],
                            vm_termination.PreemptibleInstance)

  def test_shutdown_operation(self):
    self.gce_get_ops_patch.return_value = [
        make_operation('compute.instances.guestTerminate')
    ]
    step = vm_termination.TerminationOperationType()
    with mock.patch.object(step, 'add_child') as mock_add_child:
      step.execute()
      mock_add_child.assert_called_once()
      self.assertIsInstance(mock_add_child.call_args[0][0],
                            vm_termination.GuestOsIssuedShutdown)

  def test_no_relevant_operation(self):
    self.gce_get_ops_patch.return_value = [make_operation('other-operation')]
    step = vm_termination.TerminationOperationType()
    with mock.patch.object(step, 'add_child') as mock_add_child:
      step.execute()
      mock_add_child.assert_not_called()


class Test(snapshot_test_base.RulesSnapshotTestBase):
  rule_pkg = gce
  runbook_name = 'gce/vm-termination'
  config.init({'auto': True, 'interface': 'cli'})

  rule_parameters = [{
      'project_id': 'gcpdiag-gce5-aaaa',
      'instance_name': 'start-and-stop-vm',
      'zone': 'us-central1-c',
      'start_time': '2025-03-17T00:00:00+00:00',
      'end_time': '2025-03-19T00:00:00+00:00'
  }, {
      'project_id': 'gcpdiag-gce5-aaaa',
      'instance_name': 'spot-vm-termination',
      'zone': 'us-central1-c',
      'start_time': '2025-03-17T00:00:00+00:00',
      'end_time': '2025-03-19T00:00:00+00:00'
  }, {
      'project_id': 'gcpdiag-gce5-aaaa',
      'instance_name': 'shielded-vm-integrity-failure',
      'zone': 'us-central1-c',
      'start_time': '2025-03-17T00:00:00+00:00',
      'end_time': '2025-03-19T00:00:00+00:00'
  }]
