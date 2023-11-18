# Copyright 2023 Google LLC
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
"""Test code in runbook module"""

import io
import unittest
from unittest.mock import mock_open, patch

from gcpdiag import runbook


class TestGenerateReport(unittest.TestCase):
  """Test Report Generation"""

  def make_runbook(self):

    rule = runbook.RunbookRule('test', 'test_id', 'doc_str', start_f=None)
    report = runbook.RunbookReport()
    interface = runbook.RunbookInteractionInterface(rule=rule,
                                                    runbook_report=report)
    return interface

  #pylint:disable=protected-access
  @patch('builtins.open', new_callable=mock_open)
  @patch('logging.error')
  @patch('sys.stderr', new_callable=io.StringIO)
  def test_report_to_terminal_success(self, mock_stderr, mock_logging_error,
                                      m_open):
    instance = self.make_runbook()
    json_report = '{"key": "test"}'
    instance._write_report_to_terminal(json_report)
    m_open.assert_called_once_with(instance._report_path, 'w', encoding='utf-8')
    handle = m_open.return_value.__enter__.return_value
    handle.write.assert_called_once_with(json_report)
    self.assertEqual(mock_logging_error.call_count, 0)
    self.assertIn('Runbook report located in:', mock_stderr.getvalue())

  @patch('builtins.open', side_effect=PermissionError)
  @patch('logging.error')
  @patch('sys.stderr', new_callable=io.StringIO)
  def test_save_report_permission_error(self, mock_stderr, mock_logging_error,
                                        m_open):
    json_report = '{"key": "value"}'
    instance = self.make_runbook()

    instance._write_report_to_terminal(json_report)
    m_open.assert_called_once_with(instance._report_path, 'w', encoding='utf-8')
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
    json_report = '{"key": "value"}'
    instance = self.make_runbook()

    instance._write_report_to_terminal(json_report)
    m_open.assert_called_once_with(instance._report_path, 'w', encoding='utf-8')
    handle = m_open.return_value.__enter__.return_value
    handle.write.assert_not_called()
    mock_logging_error.assert_called_once()
    assert 'Failed to save generated report to file' in mock_logging_error.call_args[
        0][0]
    # report is displayed on the terminal
    self.assertIn(json_report, mock_stderr.getvalue())
    self.assertNotIn('Runbook report located in', mock_stderr.getvalue())
