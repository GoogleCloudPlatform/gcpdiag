# Copyright 2021 Google LLC
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
"""Test Reporting Classes"""

import io
import unittest
from unittest.mock import MagicMock, mock_open, patch

from gcpdiag import config
from gcpdiag.queries import gce
from gcpdiag.runbook import report
from gcpdiag.runbook.report import StepResult

config.init({'auto': True, 'interface': 'cli'})

json_report = '{"runbook": "test/test-runbook"}'


class TestTerminalReportManager(unittest.TestCase):
  """Test Report Manager"""

  def setUp(self):
    self.trm = report.TerminalReportManager()
    self.trm.tree = MagicMock(name='MockTree')
    self.trm.tree.name = 'TestTree'
    self.resource = gce.Instance(
        'project_id', {
            'id': '123',
            'name': 'test',
            'selfLink': 'https://www.googleapis.com/compute/v1/test/test-id'
        })
    test_step = StepResult(status='ok',
                           resource=self.resource,
                           step='TestStep',
                           reason='TestReason',
                           remediation='TestRemediation',
                           remediation_skipped=True,
                           prompt_response=None)
    self.trm.results = {
        test_step.step: test_step,
    }

  def test_initialization(self):
    self.assertIsInstance(self.trm.results, dict)
    self.assertEqual(self.trm.report_path, '')

  def test_add_step_result(self):
    step_result = StepResult('ok', self.resource, 'Step1', None, None)
    self.trm.add_step_result(step_result)
    self.assertIn('Step1', self.trm.results)
    self.assertEqual(self.trm.results['Step1'], step_result)

  def test_any_failed(self):
    step_result_failed = StepResult('failed', None, 'Step1', None, None)
    self.trm.add_step_result(step_result_failed)
    self.assertTrue(self.trm.any_failed)

    step_result_ok = StepResult('ok', None, 'Step2', None, None)
    self.trm.add_step_result(step_result_ok)
    self.assertTrue(self.trm.any_failed)

  def test_get_rule_statuses(self):
    rule_statuses = self.trm.get_rule_statuses()
    self.assertEqual(rule_statuses, {'TestStep': 'ok'})

  def test_generate_report_path(self):
    with patch('gcpdiag.config.get', return_value='fake_dir') as fd:
      self.trm.get_report_path()
      self.assertTrue(self.trm.report_path.endswith('.json'))
      self.assertTrue(self.trm.report_path.startswith(fd.return_value))

  #pylint:disable=protected-access
  @patch('builtins.open', new_callable=mock_open)
  @patch('logging.error')
  @patch('sys.stderr', new_callable=io.StringIO)
  def test_report_to_terminal_success(self, mock_stderr, mock_logging_error,
                                      m_open):
    self.trm._write_report_to_terminal(json_report)
    m_open.assert_called_once_with(self.trm.report_path, 'w', encoding='utf-8')
    handle = m_open.return_value.__enter__.return_value
    handle.write.assert_called_once_with(json_report)
    self.assertEqual(mock_logging_error.call_count, 0)
    self.assertIn('Runbook report located in:', mock_stderr.getvalue())

  @patch('builtins.open', side_effect=PermissionError)
  @patch('logging.error')
  @patch('sys.stderr', new_callable=io.StringIO)
  def test_save_report_permission_error(self, mock_stderr, mock_logging_error,
                                        m_open):
    self.trm._write_report_to_terminal(json_report)
    m_open.assert_called_once_with(self.trm.report_path, 'w', encoding='utf-8')
    handle = m_open.return_value.__enter__.return_value
    handle.write.assert_not_called()
    mock_logging_error.assert_called_once()
    assert 'Permission denied' in mock_logging_error.call_args[0][0]
    # report is displayed on the terminal
    self.assertIn(json_report, mock_stderr.getvalue())
    self.assertNotIn('Runbook report located in', mock_stderr.getvalue())

  @patch('builtins.open', side_effect=OSError)
  @patch('logging.error')
  @patch('sys.stderr', new_callable=io.StringIO)
  def test_write_report_to_terminal_os_error(self, mock_stderr,
                                             mock_logging_error, m_open):

    self.trm._write_report_to_terminal(json_report)
    m_open.assert_called_once_with(self.trm.report_path, 'w', encoding='utf-8')
    handle = m_open.return_value.__enter__.return_value
    handle.write.assert_not_called()
    mock_logging_error.assert_called_once()
    assert 'Failed to save generated report to file' in mock_logging_error.call_args[
        0][0]
    # report is displayed on the terminal
    self.assertIn(json_report, mock_stderr.getvalue())
    self.assertNotIn('Runbook report located in', mock_stderr.getvalue())


class TestReportResults(unittest.TestCase):
  """Test Repor"""

  def test_initialization(self):
    resource = gce.Instance(
        'project_id', {
            'id': '123',
            'name': 'test',
            'selfLink': 'https://www.googleapis.com/compute/v1/test/test-id'
        })
    # Test normal initialization
    step_result = StepResult(status='ok',
                             resource=resource,
                             step='TestStep',
                             reason='TestReason',
                             remediation='TestRemediation',
                             remediation_skipped=False,
                             prompt_response=None)

    self.assertEqual(step_result.status, 'ok')
    self.assertEqual(str(step_result.resource), 'test/test-id')
    self.assertEqual(step_result.step, 'TestStep')
    # Add more assertions as needed

  def test_equality(self):
    # Test objects with the same properties are considered equal
    result1 = StepResult('ok', None, 'Step1', 'Reason', True)
    result2 = StepResult('ok', None, 'Step1', 'Reason', True)
    self.assertEqual(result1, result2)

    # Test objects with different properties are not considered equal
    result3 = StepResult('failed', None, 'Step1', None, None)
    self.assertNotEqual(result1, result3)
