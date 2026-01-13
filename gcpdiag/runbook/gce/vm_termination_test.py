# Copyright 2024 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# [http://www.apache.org/licenses/LICENSE-2.0](http://www.apache.org/licenses/LICENSE-2.0)
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Snapshot testing and unittest."""

import datetime
import unittest
from unittest import mock

import googleapiclient.errors

from gcpdiag.queries import apis_stub
from gcpdiag.queries import crm as crm_queries
from gcpdiag.queries import gce as gce_queries
from gcpdiag.runbook import exceptions as runbook_exceptions
from gcpdiag.runbook import op
from gcpdiag.runbook.gce import constants, flags, vm_termination

DUMMY_PROJECT_ID = 'gcpdiag-gce5-aaaa'
DUMMY_PROJECT_NUMBER = 123456012345


class MockMessage:
  """Mock messages for testing.

  Simply returns the key to verify template usage.
  """

  def get_msg(self, key, **kwargs):
    del kwargs
    return f'{key}'


class VmTerminationTestBase(unittest.TestCase):
  """Base class for VM Termination runbook tests using state-based verification."""

  def setUp(self):
    super().setUp()
    self.enterContext(
        mock.patch('gcpdiag.queries.apis.get_api', new=apis_stub.get_api_stub))

    self.mock_interface = mock.create_autospec(op.InteractionInterface,
                                               instance=True)
    self.mock_interface.rm = mock.Mock()

    self.operator = op.Operator(self.mock_interface)
    self.operator.run_id = 'test-run'
    self.operator.messages = MockMessage()

    self.params = {
        flags.PROJECT_ID:
            DUMMY_PROJECT_ID,
        flags.PROJECT_NUMBER:
            DUMMY_PROJECT_NUMBER,
        flags.INSTANCE_ID:
            '111222333',
        flags.INSTANCE_NAME:
            'test-instance',
        flags.ZONE:
            'us-central1-a',
        flags.START_TIME:
            datetime.datetime(2025, 3, 18, tzinfo=datetime.timezone.utc),
        flags.END_TIME:
            datetime.datetime(2025, 3, 19, tzinfo=datetime.timezone.utc),
    }
    self.operator.parameters = self.params

    self.mock_project = mock.Mock(spec=crm_queries.Project)
    self.mock_project.number = DUMMY_PROJECT_NUMBER
    self.enterContext(
        mock.patch(
            'gcpdiag.queries.crm.get_project',
            return_value=self.mock_project,
        ))

    self.mock_vm = mock.Mock(spec=gce_queries.Instance)
    self.mock_vm.full_path = (
        f'projects/{DUMMY_PROJECT_ID}/zones/{self.params[flags.ZONE]}/'
        f'instances/{self.params[flags.INSTANCE_NAME]}')
    self.mock_vm.name = self.params[flags.INSTANCE_NAME]
    self.mock_vm.id = self.params[flags.INSTANCE_ID]
    self.mock_vm.is_running = True
    self.mock_get_instance = self.enterContext(
        mock.patch('gcpdiag.queries.gce.get_instance',
                   return_value=self.mock_vm))

    self.gce_get_ops_patch = self.enterContext(
        mock.patch('gcpdiag.queries.gce.get_global_operations'))


def make_operation(op_type,
                   start_time='2025-03-18T12:00:00Z',
                   progress=100,
                   status_message='test',
                   user='test@example.com',
                   name='test-op'):
  """Utility to create a mock operation dictionary."""
  return {
      'operationType': op_type,
      'startTime': start_time,
      'progress': progress,
      'statusMessage': status_message,
      'user': user,
      'name': name,
  }


class TerminationOperationTypeTest(VmTerminationTestBase):
  """Test TerminationOperationType Gateway coverage."""

  def test_host_error_operation(self):
    self.gce_get_ops_patch.return_value = [
        make_operation(constants.HOST_ERROR_METHOD)
    ]
    step = vm_termination.TerminationOperationType()
    with op.operator_context(self.operator):
      self.operator.set_step(step)
      self.operator.set_step(step)
      step.execute()
      assert any(isinstance(c, vm_termination.HostError) for c in step.steps)

  def test_stop_operation(self):
    self.gce_get_ops_patch.return_value = [make_operation('stop')]
    step = vm_termination.TerminationOperationType()
    with op.operator_context(self.operator):
      self.operator.set_step(step)
      step.execute()
      assert any(
          isinstance(c, vm_termination.StopOperationGateway)
          for c in step.steps)

  def test_preempted_operation(self):
    self.gce_get_ops_patch.return_value = [
        make_operation(constants.INSTANCE_PREMPTION_METHOD)
    ]
    step = vm_termination.TerminationOperationType()
    with op.operator_context(self.operator):
      self.operator.set_step(step)
      step.execute()
      assert any(
          isinstance(c, vm_termination.PreemptibleInstance) for c in step.steps)

  def test_shutdown_operation(self):
    self.gce_get_ops_patch.return_value = [
        make_operation('compute.instances.guestTerminate')
    ]
    step = vm_termination.TerminationOperationType()
    with op.operator_context(self.operator):
      self.operator.set_step(step)
      step.execute()
      assert any(
          isinstance(c, vm_termination.GuestOsIssuedShutdown)
          for c in step.steps)

  def test_mig_repair_operation(self):
    self.gce_get_ops_patch.return_value = [
        make_operation(constants.IG_INSTANCE_REPAIR_METHOD)
    ]
    step = vm_termination.TerminationOperationType()
    with op.operator_context(self.operator):
      self.operator.set_step(step)
      step.execute()
      assert any(
          isinstance(c, vm_termination.ManagedInstanceGroupRecreation)
          for c in step.steps)

  def test_no_relevant_operation(self):
    self.gce_get_ops_patch.return_value = [make_operation('other-operation')]
    step = vm_termination.TerminationOperationType()
    with op.operator_context(self.operator):
      self.operator.set_step(step)
      step.execute()
      self.assertEqual(len(step.steps), 0)


class TestVmTerminationStubs(VmTerminationTestBase):
  """Test VM Termination runbook steps with mocks and stubs."""

  def test_is_within_window(self):
    operation = {'startTime': '2025-03-18T12:00:00Z'}
    start = self.params[flags.START_TIME]
    end = self.params[flags.END_TIME]
    self.assertTrue(vm_termination.is_within_window(operation, start, end))

  def test_start_step_instance_not_found(self):
    self.mock_get_instance.side_effect = googleapiclient.errors.HttpError(
        mock.Mock(status=404), b'Not Found')
    step = vm_termination.VmTerminationStart()
    with op.operator_context(self.operator):
      self.operator.set_step(step)
      step.execute()
    self.mock_interface.add_skipped.assert_called_once()

  def test_termination_op_type_unresolved(self):
    with op.operator_context(self.operator):
      with mock.patch(
          'gcpdiag.runbook.gce.util.ensure_instance_resolved',
          side_effect=runbook_exceptions.MissingParameterError('missing')):
        step = vm_termination.TerminationOperationType()
        self.operator.set_step(step)
        step.execute()
    self.mock_interface.add_skipped.assert_called_once()

  def test_mig_recreation_target_reached(self):
    self.mock_vm.created_by_mig = True
    self.mock_vm.mig = mock.Mock(version_target_reached=True)
    step = vm_termination.ManagedInstanceGroupRecreation()
    step.status = 'recreating'
    with op.operator_context(self.operator):
      self.operator.set_step(step)
      step.execute()
    self.mock_interface.add_failed.assert_called_once_with(
        resource=self.mock_vm,
        reason='failure_reason',
        remediation='failure_remediation',
        run_id='test-run',
        step_execution_id=mock.ANY)

  def test_preemptible_instance_skipped(self):
    self.mock_get_instance.side_effect = googleapiclient.errors.HttpError(
        mock.Mock(status=404), b'Not Found')
    step = vm_termination.PreemptibleInstance()
    with op.operator_context(self.operator):
      self.operator.set_step(step)
      step.execute()
    self.mock_interface.add_skipped.assert_called_once()

  def test_host_error_execution(self):
    step = vm_termination.HostError()
    step.status = 'Hardware failure'
    with op.operator_context(self.operator):
      self.operator.set_step(step)
      step.execute()
    self.mock_interface.add_failed.assert_called_once()

  def test_guest_os_shutdown_execution(self):
    step = vm_termination.GuestOsIssuedShutdown()
    step.status = 'Power button pressed'
    with op.operator_context(self.operator):
      self.operator.set_step(step)
      step.execute()
    self.mock_interface.add_failed.assert_called_once()

  def test_terminate_on_maintenance_execution(self):
    step = vm_termination.TerminateOnHostMaintenance()
    step.status = 'Live migration failed'
    with op.operator_context(self.operator):
      self.operator.set_step(step)
      step.execute()
    self.mock_interface.add_failed.assert_called_once()

  def test_user_stop_stopped_state(self):
    self.mock_vm.is_running = False
    step = vm_termination.UserOrServiceAccountInitiatedStop()
    step.stop_account = 'user@example.com'
    with op.operator_context(self.operator):
      self.operator.set_step(step)
      step.execute()
    self.mock_interface.add_failed.assert_called_once()

  def test_ccm_termination_api_error(self):
    type(self.mock_vm).get_network_interfaces = mock.PropertyMock(
        side_effect=googleapiclient.errors.HttpError(mock.Mock(
            status=403), b'Permission denied'))
    step = vm_termination.ComputeClusterManagerTermination()
    step.stop_account = constants.GCE_CLUSTER_MANAGER_EMAIL
    with op.operator_context(self.operator):
      self.operator.set_step(step)
      step.execute()
    self.mock_interface.add_failed.assert_called_once()
    del type(self.mock_vm).get_network_interfaces

  def test_stop_gateway_scheduled_policy(self):
    step = vm_termination.StopOperationGateway()
    step.stop_account = (
        f'service-{DUMMY_PROJECT_NUMBER}@compute-system.iam.gserviceaccount.com'
    )
    step.operation_name = 'test-op'
    with op.operator_context(self.operator):
      with mock.patch(
          'gcpdiag.queries.logs.realtime_query',
          return_value=[{
              'protoPayload': {
                  'methodName': 'ScheduledVMs'
              }
          }],
      ):
        self.operator.set_step(step)
        step.execute()
        assert any(
            isinstance(c, vm_termination.ScheduledStopPolicy)
            for c in step.steps)

  def test_start_step_instance_found_by_id(self):
    self.operator.parameters[flags.INSTANCE_NAME] = '111222333'
    step = vm_termination.VmTerminationStart()
    with op.operator_context(self.operator):
      self.operator.set_step(step)
      step.execute()
    self.assertEqual(self.operator.parameters[flags.INSTANCE_NAME],
                     self.mock_vm.name)

  def test_start_step_instance_found_by_name(self):
    self.operator.parameters[flags.INSTANCE_NAME] = 'test-instance'
    step = vm_termination.VmTerminationStart()
    with op.operator_context(self.operator):
      self.operator.set_step(step)
      step.execute()
    self.assertEqual(self.operator.parameters[flags.INSTANCE_ID],
                     self.mock_vm.id)

  def test_mig_recreation_target_not_reached(self):
    self.mock_vm.created_by_mig = True
    self.mock_vm.mig = mock.Mock(version_target_reached=False)
    step = vm_termination.ManagedInstanceGroupRecreation()
    step.status = 'recreating'
    with op.operator_context(self.operator):
      self.operator.set_step(step)
      step.execute()
    self.mock_interface.add_failed.assert_called_once_with(
        resource=self.mock_vm,
        reason='failure_reason',
        remediation='failure_remediation_a1',
        run_id='test-run',
        step_execution_id=mock.ANY)

  def test_preemptible_instance_not_running(self):
    self.mock_vm.is_preemptible_vm = True
    self.mock_vm.is_running = False
    step = vm_termination.PreemptibleInstance()
    step.status = 'preempted'
    with op.operator_context(self.operator):
      self.operator.set_step(step)
      step.execute()
    self.mock_interface.add_failed.assert_called_once_with(
        resource=self.mock_vm,
        reason='failure_reason',
        remediation='failure_remediation_a1',
        run_id='test-run',
        step_execution_id=mock.ANY)

  def test_ccm_termination_shared_vpc(self):
    self.mock_vm.get_network_interfaces = [{
        'network':
            'https://www.googleapis.com/compute/v1/projects/shared-vpc-host/global/networks/vpc-1'
    }]
    step = vm_termination.ComputeClusterManagerTermination()
    step.stop_account = constants.GCE_CLUSTER_MANAGER_EMAIL
    with op.operator_context(self.operator):
      self.operator.set_step(step)
      step.execute()
    self.mock_interface.add_failed.assert_called_once()

  def test_stop_gateway_user_stop(self):
    step = vm_termination.StopOperationGateway()
    step.stop_account = 'user@example.com'
    step.operation_name = 'test-op'
    with op.operator_context(self.operator):
      self.operator.set_step(step)
      step.execute()
      self.assertTrue(
          any(
              isinstance(c, vm_termination.UserOrServiceAccountInitiatedStop)
              for c in step.steps))

  def test_stop_gateway_ccm_termination(self):
    step = vm_termination.StopOperationGateway()
    step.stop_account = constants.GCE_CLUSTER_MANAGER_EMAIL
    step.operation_name = 'test-op'
    with op.operator_context(self.operator):
      self.operator.set_step(step)
      step.execute()
      self.assertTrue(
          any(
              isinstance(c, vm_termination.ComputeClusterManagerTermination)
              for c in step.steps))

  def test_scheduled_stop_policy_running(self):
    self.mock_vm.is_running = True
    step = vm_termination.ScheduledStopPolicy()
    step.stop_account = f'service-{DUMMY_PROJECT_NUMBER}@compute-system.iam.gserviceaccount.com'
    with op.operator_context(self.operator):
      self.operator.set_step(step)
      step.execute()
    self.mock_interface.add_failed.assert_called_once_with(
        resource=self.mock_vm,
        reason='failure_reason',
        remediation='failure_remediation',
        run_id='test-run',
        step_execution_id=mock.ANY)

  def test_vm_termination_end_satisfied(self):
    step = vm_termination.VmTerminationEnd()
    with op.operator_context(self.operator):
      with mock.patch('gcpdiag.runbook.op.prompt', return_value=op.YES):
        self.operator.set_step(step)
        step.execute()
        self.operator.interface.rm.generate_report.assert_not_called()
