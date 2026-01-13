# Copyright 2025 Google LLC
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
"""Test class for gce/GuestosBootup."""

import datetime
import unittest
from unittest import mock

import googleapiclient.errors

from gcpdiag import config, runbook
from gcpdiag.queries import gce as gce_queries
from gcpdiag.runbook import gce, op, snapshot_test_base
from gcpdiag.runbook.gce import flags, guestos_bootup


class MockMessage:
  """Mock messages for testing."""

  def get_msg(self, key, **kwargs):
    del kwargs
    return f'{key}'


class BootupStepTestBase(unittest.TestCase):
  """Base class for bootup tests."""

  def setUp(self):
    super().setUp()
    self.mock_op_get = self.enterContext(mock.patch('gcpdiag.runbook.op.get'))
    self.mock_op_put = self.enterContext(mock.patch('gcpdiag.runbook.op.put'))
    self.mock_op_add_ok = self.enterContext(
        mock.patch('gcpdiag.runbook.op.add_ok'))
    self.mock_op_add_failed = self.enterContext(
        mock.patch('gcpdiag.runbook.op.add_failed'))
    self.mock_op_add_skipped = self.enterContext(
        mock.patch('gcpdiag.runbook.op.add_skipped'))
    self.mock_gce_get_instance = self.enterContext(
        mock.patch('gcpdiag.queries.gce.get_instance'))
    self.mock_crm_get_project = self.enterContext(
        mock.patch('gcpdiag.queries.crm.get_project', return_value=mock.Mock()))

    self.mock_instance = mock.Mock(spec=gce_queries.Instance)
    self.mock_instance.project_id = 'test-project'
    self.mock_instance.zone = 'us-central1-a'
    self.mock_instance.name = 'test-instance'
    self.mock_instance.id = '12345'
    self.mock_instance.is_running = True
    self.mock_gce_get_instance.return_value = self.mock_instance

    self.params = {
        flags.PROJECT_ID: 'test-project',
        flags.ZONE: 'us-central1-a',
        flags.INSTANCE_NAME: 'test-instance',
        flags.INSTANCE_ID: None,
        flags.SERIAL_CONSOLE_FILE: None,
        flags.START_TIME: datetime.datetime(2025, 10, 27),
        flags.END_TIME: datetime.datetime(2025, 10, 28),
    }
    self.mock_op_get.side_effect = lambda key, default=None: self.params.get(
        key, default)

    # Setup operator context
    mock_interface = mock.Mock()
    operator = op.Operator(mock_interface)
    operator.messages = MockMessage()
    operator.parameters = self.params
    operator.run_id = 'test-run-id'
    mock_step = mock.Mock()
    mock_step.execution_id = 'test-step-id'
    self.enterContext(
        mock.patch.object(op.Operator,
                          'step',
                          new_callable=mock.PropertyMock,
                          return_value=mock_step))
    self.enterContext(op.operator_context(operator))


class GuestosBootupStartTest(BootupStepTestBase):

  def test_instance_id_missing(self):
    self.mock_instance.is_running = True
    self.params[flags.INSTANCE_ID] = None
    step = guestos_bootup.GuestosBootupStart()
    step.execute()
    self.mock_op_put.assert_any_call(flags.INSTANCE_ID, '12345')

  def test_instance_name_missing(self):
    self.mock_instance.is_running = True
    self.params[flags.INSTANCE_NAME] = None
    # Must provide ID if name is missing for realistic resolution
    self.params[flags.INSTANCE_ID] = '12345'
    step = guestos_bootup.GuestosBootupStart()
    step.execute()
    self.mock_op_put.assert_any_call(flags.INSTANCE_NAME, 'test-instance')

  def test_instance_not_found(self):
    self.mock_gce_get_instance.side_effect = googleapiclient.errors.HttpError(
        mock.Mock(status=404), b'not found')
    step = guestos_bootup.GuestosBootupStart()
    step.execute()
    self.mock_op_add_skipped.assert_called_once()

  def test_instance_not_running(self):
    self.mock_instance.is_running = False
    self.mock_instance.status = 'TERMINATED'
    step = guestos_bootup.GuestosBootupStart()
    step.execute()
    self.mock_op_add_failed.assert_called_once()

  def test_serial_file_not_found(self):
    self.params[flags.SERIAL_CONSOLE_FILE] = 'nonexistent.log'
    with mock.patch('builtins.open', side_effect=FileNotFoundError):
      step = guestos_bootup.GuestosBootupStart()
      step.execute()
      self.mock_op_add_skipped.assert_called_once()
      self.assertIn('does not exists',
                    self.mock_op_add_skipped.call_args[1]['reason'])

  def test_serial_file_compressed(self):
    self.params[flags.SERIAL_CONSOLE_FILE] = 'compressed.log.gz'
    m = mock.mock_open(read_data=b'\x1f\x8b' + b' compressed data')
    with (
        mock.patch('builtins.open', m),
        mock.patch('mimetypes.guess_type',
                   return_value=('application/gzip', 'gzip')),
    ):
      step = guestos_bootup.GuestosBootupStart()
      step.execute()
      self.mock_op_add_skipped.assert_called_once()
      self.assertIn(
          'appears to be compressed',
          self.mock_op_add_skipped.call_args[1]['reason'],
      )

  def test_serial_file_not_plain_text(self):
    self.params[flags.SERIAL_CONSOLE_FILE] = 'binary.log'
    # 0xff is invalid in utf-8
    m = mock.mock_open(read_data=b'\x01\x02\xff\xfe')
    with (
        mock.patch('builtins.open', m),
        mock.patch(
            'mimetypes.guess_type',
            return_value=('application/octet-stream', None),
        ),
    ):
      step = guestos_bootup.GuestosBootupStart()
      step.execute()
      self.mock_op_add_skipped.assert_called_once()
      self.assertIn(
          'does not appear to be plain text',
          self.mock_op_add_skipped.call_args[1]['reason'],
      )

  def test_serial_valid_file(self):
    self.params[flags.SERIAL_CONSOLE_FILE] = 'valid.log'
    m = mock.mock_open(read_data=b'plain text log')
    with (
        mock.patch('builtins.open', m),
        mock.patch('mimetypes.guess_type', return_value=('text/plain', None)),
    ):
      step = guestos_bootup.GuestosBootupStart()
      step.execute()
      self.mock_op_add_skipped.assert_not_called()


class CloudInitChecksTest(BootupStepTestBase):

  def setUp(self):
    super().setUp()
    self.mock_gce_get_gce_public_licences = self.enterContext(
        mock.patch('gcpdiag.queries.gce.get_gce_public_licences',
                   return_value=['license1']))
    self.mock_vm_serial_logs_check = self.enterContext(
        mock.patch('gcpdiag.runbook.gce.generalized_steps.VmSerialLogsCheck'))
    self.mock_add_child = self.enterContext(
        mock.patch(
            'gcpdiag.runbook.gce.guestos_bootup.CloudInitChecks.add_child'))

  def test_ubuntu_license_present(self):
    self.mock_instance.check_license.return_value = True
    step = guestos_bootup.CloudInitChecks()
    step.execute()
    self.mock_instance.check_license.assert_called_once()
    self.assertEqual(self.mock_add_child.call_count, 2)
    self.mock_op_add_skipped.assert_not_called()

  def test_ubuntu_license_not_present(self):
    self.mock_instance.check_license.return_value = False
    step = guestos_bootup.CloudInitChecks()
    step.execute()
    self.mock_instance.check_license.assert_called_once()
    self.mock_add_child.assert_not_called()
    self.mock_op_add_skipped.assert_called_once()


class GuestosBootupBuildTreeTest(unittest.TestCase):

  def test_build_tree(self):
    self.mock_op_get = self.enterContext(mock.patch('gcpdiag.runbook.op.get'))
    self.params = {
        flags.PROJECT_ID: 'test-project',
        flags.ZONE: 'us-central1-a',
        flags.INSTANCE_NAME: 'test-instance',
    }
    self.mock_op_get.side_effect = lambda key, default=None: self.params.get(
        key, default)

    tree = guestos_bootup.GuestosBootup()
    tree.build_tree()
    self.assertIsInstance(tree.start, guestos_bootup.GuestosBootupStart)
    children = tree.start.steps
    self.assertEqual(len(children), 6)
    self.assertEqual(children[0].template, 'vm_serial_log::kernel_panic')
    self.assertEqual(children[1].template, 'vm_serial_log::linux_fs_corruption')
    self.assertIsInstance(children[2], guestos_bootup.CloudInitChecks)
    self.assertEqual(children[3].template, 'vm_serial_log::network_errors')
    self.assertEqual(children[4].template, 'vm_serial_log::guest_agent')
    self.assertIsInstance(children[5], runbook.EndStep)


class Test(snapshot_test_base.RulesSnapshotTestBase):
  rule_pkg = gce
  runbook_name = 'gce/guestos-bootup'
  config.init({'auto': True, 'interface': 'cli'})

  rule_parameters = [{
      'project_id': 'gcpdiag-gce-vm-performance',
      'instance_name': 'faulty-linux-ssh',
      'zone': 'europe-west2-a'
  }, {
      'project_id': 'gcpdiag-gce-vm-performance',
      'instance_name': 'valid-linux-ssh',
      'zone': 'europe-west2-a'
  }]
