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
from unittest.mock import mock_open, patch

from gcpdiag import config
from gcpdiag.queries import gce
from gcpdiag.runbook import Step, report
from gcpdiag.runbook.report import StepResult

config.init({'auto': True, 'interface': 'cli'})

json_report = '{"runbook": "test/test-runbook"}'


class TestTerminalReportManager(unittest.TestCase):
  """Test Report Manager"""

  def setUp(self):
    self.trm = report.TerminalReportManager()
    r = report.Report(run_id='test', parameters={})
    r.run_id = 'test'
    self.trm.reports[r.run_id] = r
    self.resource = gce.Instance(
        'project_id', {
            'id': '123',
            'name': 'test',
            'selfLink': 'https://www.googleapis.com/compute/v1/test/test-id'
        })

    ok_step_eval = report.ResourceEvaluation(resource=self.resource,
                                             status='ok',
                                             reason='TestReason',
                                             remediation='TestRemediation')
    test_step = report.StepResult(step=Step(uuid='ok.step'))

    test_step.results.append(ok_step_eval)
    self.trm.reports['test'].results = {
        test_step.execution_id: test_step,
    }

  def test_initialization(self):
    self.assertIsInstance(self.trm.reports['test'].results, dict)

  def test_add_step_result(self):
    step_result = StepResult(Step(uuid='friendly.name'))
    self.trm.add_step_result(run_id='test', result=step_result)
    self.assertIn('gcpdiag.runbook.Step.friendly.name',
                  self.trm.reports['test'].results)
    self.assertEqual(
        self.trm.reports['test'].results['gcpdiag.runbook.Step.friendly.name'],
        step_result)

  def test_any_failed(self):
    step_result_failed = StepResult(Step(uuid='failed'))
    failed_eval = report.ResourceEvaluation(resource=self.resource,
                                            status='failed',
                                            reason='TestReason',
                                            remediation='TestRemediation')
    self.trm.add_step_result(run_id='test', result=step_result_failed)
    self.trm.add_step_eval(run_id='test',
                           execution_id=step_result_failed.execution_id,
                           evaluation=failed_eval)
    self.assertTrue(self.trm.reports['test'].any_failed)

  def test_get_rule_statuses(self):
    rule_statuses = self.trm.reports['test'].get_rule_statuses()
    self.assertEqual(rule_statuses, {'gcpdiag.runbook.Step.ok.step': 'ok'})

  def test_generate_report_path(self):
    with patch('gcpdiag.config.get', return_value='fake_dir') as fd:
      report_path = self.trm.get_report_path('test')
      self.assertTrue(report_path.endswith('.json'))
      self.assertTrue(report_path.startswith(fd.return_value))

  #pylint:disable=protected-access
  @patch('builtins.open', new_callable=mock_open)
  @patch('logging.error')
  @patch('sys.stderr', new_callable=io.StringIO)
  def test_report_to_terminal_success(self, mock_stderr, mock_logging_error,
                                      m_open):
    report_path = self.trm.get_report_path('test')
    self.trm._write_report_to_terminal(out_path=report_path,
                                       json_report=json_report)
    m_open.assert_called_once_with(report_path, 'w', encoding='utf-8')
    handle = m_open.return_value.__enter__.return_value
    handle.write.assert_called_once_with(json_report)
    self.assertEqual(mock_logging_error.call_count, 0)
    self.assertIn('Runbook report located in:', mock_stderr.getvalue())

  @patch('builtins.open', side_effect=PermissionError)
  @patch('logging.error')
  @patch('sys.stderr', new_callable=io.StringIO)
  def test_save_report_permission_error(self, mock_stderr, mock_logging_error,
                                        m_open):
    report_path = self.trm.get_report_path('test')
    self.trm._write_report_to_terminal(out_path=report_path,
                                       json_report=json_report)
    m_open.assert_called_once_with(report_path, 'w', encoding='utf-8')
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

    report_path = self.trm.get_report_path('test')
    self.trm._write_report_to_terminal(out_path=report_path,
                                       json_report=json_report)
    m_open.assert_called_once_with(report_path, 'w', encoding='utf-8')
    handle = m_open.return_value.__enter__.return_value
    handle.write.assert_not_called()
    mock_logging_error.assert_called_once()
    assert 'Failed to save generated report to file' in mock_logging_error.call_args[
        0][0]
    # report is displayed on the terminal
    self.assertIn(json_report, mock_stderr.getvalue())
    self.assertNotIn('Runbook report located in', mock_stderr.getvalue())


class TestReportResults(unittest.TestCase):
  """Test Report"""

  def test_initialization(self):
    resource = gce.Instance(
        'project_id', {
            'id': '123',
            'name': 'test',
            'selfLink': 'https://www.googleapis.com/compute/v1/test/test-id'
        })
    # Test normal initialization
    ok_step_eval = report.ResourceEvaluation(resource=resource,
                                             status='ok',
                                             reason='TestReason',
                                             remediation='TestRemediation')
    step_result = report.StepResult(step=Step(uuid='ok.step.friendly.name'))
    step_result.results.append(ok_step_eval)

    self.assertEqual(step_result.overall_status, 'ok')

  def test_equality(self):
    # Test objects with the same properties are considered equal
    result1 = StepResult(Step(uuid='uuid'))
    result2 = StepResult(Step(uuid='uuid'))
    self.assertEqual(result1, result2)

    # Test objects with different properties are not considered equal
    result3 = StepResult(Step())
    self.assertNotEqual(result1, result3)
