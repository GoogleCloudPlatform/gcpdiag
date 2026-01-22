# Copyright 2022 Google LLC
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
"""Test class for gce/serial-log-analyzer."""

from unittest import mock

import apiclient.errors

from gcpdiag import config
from gcpdiag.queries import apis_stub
from gcpdiag.runbook import gce, op, snapshot_test_base
from gcpdiag.runbook.gce import flags, serial_log_analyzer
from gcpdiag.runbook.gce.generalized_steps_test import GceStepTestBase


class Test(snapshot_test_base.RulesSnapshotTestBase):
  rule_pkg = gce
  runbook_name = 'gce/serial-log-analyzer'
  config.init({'auto': True, 'interface': 'cli'})

  rule_parameters = [{
      'project_id': 'gcpdiag-gce-vm-performance',
      'instance_name': 'faulty-linux-ssh',
      'zone': 'europe-west2-a'
  }, {
      'project_id': 'gcpdiag-gce-vm-performance',
      'name': 'valid-linux-ssh',
      'zone': 'europe-west2-a'
  }]


class SerialLogAnalyzerTreeTest(GceStepTestBase):
  """Test SerialLogAnalyzer tree building and parameter handling."""

  def test_build_tree(self):
    """Ensure the diagnostic tree is built by providing operator context."""
    tree = serial_log_analyzer.SerialLogAnalyzer()
    operator = op.Operator(interface=mock.Mock(), context_provider=mock.Mock())
    operator.set_parameters(self.params)

    with op.operator_context(operator):
      tree.build_tree()

    self.assertIsNotNone(tree.start)
    self.assertIsInstance(tree.start,
                          serial_log_analyzer.SerialLogAnalyzerStart)

    diagnostic_steps = tree.start.steps[0].steps
    step_types = [type(step) for step in diagnostic_steps]

    self.assertIn(serial_log_analyzer.CloudInitChecks, step_types)

  def test_legacy_parameter_handler(self):
    """Test mapping of deprecated 'name' to 'instance_name'."""
    tree = serial_log_analyzer.SerialLogAnalyzer()
    params = {flags.NAME: 'legacy-vm-name'}
    tree.legacy_parameter_handler(params)
    self.assertEqual(params[flags.INSTANCE_NAME], 'legacy-vm-name')
    self.assertNotIn(flags.NAME, params)


class SerialLogAnalyzerStartTest(GceStepTestBase):
  """Test SerialLogAnalyzerStart execution."""

  def setUp(self):
    super().setUp()
    self.mock_crm_get_project = self.enterContext(
        mock.patch('gcpdiag.queries.crm.get_project'))
    self.mock_gce_get_instance.return_value = self.mock_instance
    self.enterContext(
        mock.patch('gcpdiag.queries.apis.get_api', new=apis_stub.get_api_stub))

  def test_start_success(self):
    """Test successful VM detail fetching and ID assignment (Lines 255-270)."""
    self.mock_instance.is_running = True
    self.mock_instance.id = '12345'
    step = serial_log_analyzer.SerialLogAnalyzerStart()
    step.execute()
    self.mock_op_put.assert_any_call(flags.ID, '12345')

  def test_start_updates_missing_instance_name(self):
    """Test updating missing instance name from VM metadata."""
    self.mock_instance.is_running = True
    self.mock_instance.name = 'metadata-name'
    # Simulate ID present but instance_name missing in op context
    op_values = {
        flags.ID: '123',
        flags.PROJECT_ID: 'test-project',
    }
    with mock.patch.object(serial_log_analyzer.op,
                           'get',
                           side_effect=op_values.get):
      step = serial_log_analyzer.SerialLogAnalyzerStart()
      step.execute()
      self.mock_op_put.assert_any_call(flags.INSTANCE_NAME, 'metadata-name')

  def test_instance_not_found_error_handling(self):
    """Test handling of API errors."""
    self.mock_gce_get_instance.side_effect = apiclient.errors.HttpError(
        mock.Mock(status=404), b'not found')
    step = serial_log_analyzer.SerialLogAnalyzerStart()
    step.execute()
    self.mock_op_add_skipped.assert_called_once()

  @mock.patch('builtins.open',
              new_callable=mock.mock_open,
              read_data=b'plain text')
  @mock.patch('mimetypes.guess_type')
  def test_serial_console_file_checks(self, mock_guess, mock_open):
    """Test sanity checks for local log files."""
    self.mock_instance.is_running = True
    self.params[flags.SERIAL_CONSOLE_FILE] = 'test_logs.txt'
    mock_guess.return_value = ('text/plain', None)
    step = serial_log_analyzer.SerialLogAnalyzerStart()
    step.execute()
    mock_open.assert_called_with('test_logs.txt', 'rb')

  @mock.patch('builtins.open',
              new_callable=mock.mock_open,
              read_data=b'\x1f\x8b\x08')
  @mock.patch('mimetypes.guess_type')
  def test_serial_console_file_compressed(self, mock_guess, unused_mock_open):
    """Test detection of compressed files via magic number."""
    self.mock_instance.is_running = True
    self.params[flags.SERIAL_CONSOLE_FILE] = 'logs.gz'
    mock_guess.return_value = ('application/gzip', None)
    step = serial_log_analyzer.SerialLogAnalyzerStart()
    step.execute()
    self.mock_op_add_skipped.assert_called_with(
        mock.ANY,
        reason='File logs.gz appears to be compressed, not plain text.')

  @mock.patch('builtins.open',
              new_callable=mock.mock_open,
              read_data=b'\xff\xfe\xfd')
  @mock.patch('mimetypes.guess_type')
  def test_serial_console_file_binary_error(self, mock_guess, unused_mock_open):
    """Test handling of non-UTF8 binary files."""
    self.mock_instance.is_running = True
    self.params[flags.SERIAL_CONSOLE_FILE] = 'binary.bin'
    mock_guess.return_value = ('application/octet-stream', None)
    step = serial_log_analyzer.SerialLogAnalyzerStart()
    step.execute()
    self.mock_op_add_skipped.assert_called_with(
        mock.ANY, reason='File binary.bin does not appear to be plain text.')


class CloudInitChecksTest(GceStepTestBase):
  """Test CloudInitChecks logic."""

  def setUp(self):
    super().setUp()
    self.enterContext(
        mock.patch('gcpdiag.queries.apis.get_api', new=apis_stub.get_api_stub))
    self.mock_add_child = self.enterContext(
        mock.patch.object(serial_log_analyzer.CloudInitChecks, 'add_child'))

  def test_ubuntu_triggers_child_steps(self):
    """Test child steps are added for Ubuntu instances."""
    self.mock_instance.check_license.return_value = True
    step = serial_log_analyzer.CloudInitChecks()
    step.execute()

    self.assertEqual(len(self.mock_add_child.call_args_list), 2)

    added_steps = [args[0][0] for args in self.mock_add_child.call_args_list]
    self.assertIsInstance(added_steps[0],
                          serial_log_analyzer.gce_gs.VmSerialLogsCheck)
    self.assertIsInstance(added_steps[1],
                          serial_log_analyzer.gce_gs.VmSerialLogsCheck)

  def test_non_ubuntu_skips_checks(self):
    """Test skipping checks for non-Ubuntu OS."""
    self.mock_instance.check_license.return_value = False
    step = serial_log_analyzer.CloudInitChecks()
    step.execute()
    self.mock_op_add_skipped.assert_called_once()


class AnalysingSerialLogsEndTest(GceStepTestBase):
  """Test AnalysingSerialLogsEnd termination."""

  def test_end_step_output_non_interactive(self):
    """Test that the end message is displayed correctly in non-interactive mode."""
    with (
        mock.patch.object(serial_log_analyzer.config, 'get',
                          return_value=False),
        mock.patch.object(serial_log_analyzer.op, 'prompt', return_value=op.NO),
        mock.patch.object(serial_log_analyzer.op, 'info') as mock_info,
    ):
      step = serial_log_analyzer.AnalysingSerialLogsEnd()
      step.execute()
      mock_info.assert_called_with(message=op.END_MESSAGE)

  def test_end_step_output_interactive_mode(self):
    """Test that the end message is skipped in interactive mode."""
    with (
        mock.patch.object(serial_log_analyzer.config, 'get', return_value=True),
        mock.patch.object(serial_log_analyzer.op, 'prompt') as mock_prompt,
        mock.patch.object(serial_log_analyzer.op, 'info') as mock_info,
    ):
      step = serial_log_analyzer.AnalysingSerialLogsEnd()
      step.execute()
      mock_prompt.assert_not_called()
      mock_info.assert_not_called()
