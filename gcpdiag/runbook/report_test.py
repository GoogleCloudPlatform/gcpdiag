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
from unittest.mock import Mock, PropertyMock, mock_open, patch

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

  def test_add_step_prompt_response(self):
    step_result = StepResult(Step(uuid='prompt.response.step'))
    self.trm.add_step_result(run_id='test', result=step_result)
    prompt_response = 'continue'
    self.trm.add_step_prompt_response(
        run_id='test',
        execution_id=step_result.execution_id,
        prompt_response=prompt_response,
    )
    self.assertEqual(
        self.trm.reports['test'].results[
            step_result.execution_id].prompt_response,
        prompt_response,
    )

  def test_report_any_failed_uncertain(self):
    self.trm.reports['test'].results['gcpdiag.runbook.Step.ok.step'].results[
        0].status = 'ok'
    self.assertFalse(self.trm.reports['test'].any_failed)
    step_result_uncertain = StepResult(Step(uuid='uncertain'))
    uncertain_eval = report.ResourceEvaluation(resource=self.resource,
                                               status='uncertain',
                                               reason='TestReason',
                                               remediation='TestRemediation')
    self.trm.add_step_result(run_id='test', result=step_result_uncertain)
    self.trm.add_step_eval(run_id='test',
                           execution_id=step_result_uncertain.execution_id,
                           evaluation=uncertain_eval)
    self.assertTrue(self.trm.reports['test'].any_failed)

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

  def test_add_step_metadata(self):
    step_result = StepResult(Step(uuid='metadata.step'))
    self.trm.add_step_result(run_id='test', result=step_result)
    self.trm.add_step_metadata(run_id='test',
                               key='foo',
                               value='bar',
                               step_execution_id=step_result.execution_id)
    self.assertEqual(
        self.trm.reports['test'].results[
            step_result.execution_id].metadata['foo'], 'bar')
    self.assertEqual(
        self.trm.get_step_metadata(run_id='test',
                                   key='foo',
                                   step_execution_id=step_result.execution_id),
        'bar')
    self.assertEqual(
        self.trm.get_all_step_metadata(
            run_id='test', step_execution_id=step_result.execution_id),
        {'foo': 'bar'})

  def test_get_all_step_metadata_no_id(self):
    self.assertEqual(
        self.trm.get_all_step_metadata(run_id='test', step_execution_id=None),
        {})

  def test_add_step_info_metadata(self):
    step_result = StepResult(Step(uuid='info.metadata.step'))
    self.trm.add_step_result(run_id='test', result=step_result)
    self.trm.add_step_info_metadata(run_id='test',
                                    value='info_message',
                                    step_execution_id=step_result.execution_id)
    self.assertIn(
        'info_message',
        self.trm.reports['test'].results[step_result.execution_id].info)

  def test_add_step_metadata_no_id(self):
    self.trm.add_step_metadata(run_id='test',
                               key='foo',
                               value='bar',
                               step_execution_id=None)
    # in this case nothing is done, so no assertion needed
    # besides verifying no crash

  def test_get_step_metadata_no_id(self):
    self.assertIsNone(
        self.trm.get_step_metadata(run_id='test',
                                   key='foo',
                                   step_execution_id=None))

  def test_report_any_failed(self):
    self.trm.reports['test'].results['gcpdiag.runbook.Step.ok.step'].results[
        0].status = 'ok'
    self.assertFalse(self.trm.reports['test'].any_failed)
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

  @patch(
      'gcpdiag.runbook.report.TerminalReportManager._write_report_to_terminal')
  def test_trm_generate_reports(self, mock_write_report):
    self.trm.reports['test'].run_start_time = '2023-01-01T00:00:00Z'
    self.trm.reports['test'].run_end_time = '2023-01-01T00:00:01Z'
    self.trm.reports['test'].results[
        'gcpdiag.runbook.Step.ok.step'].start_time = '2023-01-01T00:00:00Z'
    self.trm.reports['test'].results[
        'gcpdiag.runbook.Step.ok.step'].end_time = '2023-01-01T00:00:01Z'
    self.trm.reports['test'].results[
        'gcpdiag.runbook.Step.ok.step'].step.name = ' step name '
    result = self.trm.generate_reports()
    mock_write_report.assert_called_once()
    self.assertIsInstance(result, dict)
    self.assertEqual(result['run_id'], 'test')

  def test_generate_report_metrics_no_runbook_name(self):
    step_result = self.trm.reports['test'].results[
        'gcpdiag.runbook.Step.ok.step']
    step_result.step = Mock()
    step_result.step.id = 'ok.step'
    self.trm.reports['test'].run_start_time = '2023-01-01T00:00:00Z'
    self.trm.reports['test'].run_end_time = '2023-01-01T00:00:01Z'
    step_result.start_time = '2023-01-01T00:00:00Z'
    step_result.end_time = '2023-01-01T00:00:01Z'
    self.trm.reports['test'].runbook_name = None
    metrics = self.trm.generate_report_metrics(self.trm.reports['test'])
    self.assertNotIn('runbook_name', metrics)
    self.assertNotIn('run_duration', metrics)
    self.assertNotIn('totals_by_status', metrics)
    self.assertIn('steps', metrics)
    self.assertIn('ok.step', metrics['steps'][0])
    self.assertEqual(metrics['steps'][0]['ok.step']['execution_duration'], 1000)

  def test_get_totals_by_status(self):
    totals = self.trm.get_totals_by_status()
    self.assertEqual(totals['ok'], 1)

  def test_generate_report_metrics(self):
    step_result = self.trm.reports['test'].results[
        'gcpdiag.runbook.Step.ok.step']
    step_result.step = Mock()
    step_result.step.id = 'ok.step'
    self.trm.reports['test'].run_start_time = '2023-01-01T00:00:00Z'
    self.trm.reports['test'].run_end_time = '2023-01-01T00:00:01Z'
    step_result.start_time = '2023-01-01T00:00:00Z'
    step_result.end_time = '2023-01-01T00:00:01Z'
    self.trm.reports['test'].runbook_name = 'test/test-runbook'
    metrics = self.trm.generate_report_metrics(self.trm.reports['test'])
    self.assertIn('runbook_name', metrics)
    self.assertEqual(metrics['run_duration'], 1000)
    self.assertIn('ok.step', metrics['steps'][0])
    self.assertEqual(metrics['steps'][0]['ok.step']['execution_duration'], 1000)

  @patch('builtins.open', new_callable=mock_open)
  def test_generate_reports_no_reports(self, m_open):
    trm = report.TerminalReportManager()
    with self.assertRaises(UnboundLocalError):
      trm.generate_reports()
    m_open.assert_not_called()

  def test_serialize_report_with_formatting(self):
    self.trm.reports['test'].run_start_time = '2023-01-01T00:00:00Z'
    self.trm.reports['test'].run_end_time = '2023-01-01T00:00:01Z'
    step_result = self.trm.reports['test'].results[
        'gcpdiag.runbook.Step.ok.step']
    step_result.start_time = '2023-01-01T00:00:00Z'
    step_result.end_time = '2023-01-01T00:00:01Z'
    step_result.step.name = ' step name '
    step_result.results[0].reason = ' reason\\nnewline '
    serialized = self.trm.serialize_report(self.trm.reports['test'])
    self.assertIn('"name": "step name"', serialized)
    self.assertIn('"reason": "reason\\nnewline"', serialized)


class TestReportResults(unittest.TestCase):
  """Test Report"""

  def test_overall_status_no_status(self):
    step_result = report.StepResult(step=Step(uuid='no.status.step'))
    self.assertEqual(step_result.overall_status, 'no_status')

  def test_step_result_any_failed(self):
    resource = gce.Instance(
        'project_id', {
            'id': '123',
            'name': 'test',
            'selfLink': 'https://www.googleapis.com/compute/v1/test/test-id'
        })
    failed_eval = report.ResourceEvaluation(resource=resource,
                                            status='failed',
                                            reason='TestReason',
                                            remediation='TestRemediation')
    step_result = report.StepResult(step=Step(uuid='failed.step'))
    step_result.results.append(failed_eval)
    self.assertTrue(step_result.any_failed)

  def test_hash(self):
    step_result = report.StepResult(step=Step(uuid='ok.step'))
    self.assertEqual(hash(step_result), hash(step_result.execution_id))

  def test_equality(self):
    # Test objects with the same properties are considered equal
    result1 = StepResult(Step(uuid='uuid'))
    result2 = StepResult(Step(uuid='uuid'))
    self.assertEqual(result1, result2)

    # Test objects with different properties are not considered equal
    result3 = StepResult(Step())
    self.assertNotEqual(result1, result3)

  def test_overall_status_with_step_error(self):
    step_result = report.StepResult(step=Step(uuid='error.step'))
    step_result.step_error = 'some error'
    self.assertEqual(step_result.overall_status, 'skipped')

  def test_overall_status_no_results(self):
    step_result = report.StepResult(step=Step(uuid='no.results.step'))
    self.assertEqual(step_result.overall_status, 'no_status')

  def test_any_uncertain(self):
    resource = gce.Instance(
        'project_id', {
            'id': '123',
            'name': 'test',
            'selfLink': 'https://www.googleapis.com/compute/v1/test/test-id'
        })
    uncertain_eval = report.ResourceEvaluation(resource=resource,
                                               status='uncertain',
                                               reason='TestReason',
                                               remediation='TestRemediation')
    step_result = report.StepResult(step=Step(uuid='uncertain.step'))
    step_result.results.append(uncertain_eval)
    self.assertTrue(step_result.any_uncertain)
    self.assertEqual(step_result.overall_status, 'uncertain')

  def test_any_failed(self):
    resource = gce.Instance(
        'project_id', {
            'id': '123',
            'name': 'test',
            'selfLink': 'https://www.googleapis.com/compute/v1/test/test-id'
        })
    failed_eval = report.ResourceEvaluation(resource=resource,
                                            status='failed',
                                            reason='TestReason',
                                            remediation='TestRemediation')
    step_result = report.StepResult(step=Step(uuid='failed.step'))
    step_result.results.append(failed_eval)
    self.assertTrue(step_result.any_failed)
    self.assertEqual(step_result.overall_status, 'failed')


class TestApiReportManager(unittest.TestCase):
  """Test ApiReportManager"""

  def setUp(self):
    self.arm = report.ApiReportManager()
    r = report.Report(run_id='test', parameters={})
    r.run_id = 'test'
    r.run_start_time = '2023-01-01T00:00:00Z'
    r.run_end_time = '2023-01-01T00:00:01Z'
    self.arm.reports[r.run_id] = r
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
    test_step.start_time = '2023-01-01T00:00:00Z'
    test_step.end_time = '2023-01-01T00:00:01Z'

    test_step.results.append(ok_step_eval)
    self.arm.reports['test'].results = {
        test_step.execution_id: test_step,
    }

  @patch('gcpdiag.runbook.Step.name', new_callable=PropertyMock)
  def test_generate_reports(self, mock_name):
    mock_name.return_value = 'test step'
    reports = self.arm.generate_reports()
    self.assertEqual(len(reports), 1)
    self.assertEqual(reports[0]['run_id'], 'test')


class TestInteractionInterface(unittest.TestCase):
  """Test InteractionInterface"""

  def setUp(self):
    self.addCleanup(config.init, {'auto': True, 'interface': 'cli'})
    config.init({'auto': False, 'interface': 'cli'})
    self.cli_interface = report.InteractionInterface(kind='cli')
    self.api_interface = report.InteractionInterface(kind='api')
    self.resource = gce.Instance(
        'project_id', {
            'id': '123',
            'name': 'test',
            'selfLink': 'https://www.googleapis.com/compute/v1/test/test-id'
        })

  def test_invalid_interface(self):
    with self.assertRaises(AttributeError):
      report.InteractionInterface(kind='invalid')

  @patch('gcpdiag.runbook.output.terminal_output.TerminalOutput.info')
  def test_info(self, mock_info):
    self.cli_interface.info('test message')
    mock_info.assert_called_with(message='test message', step_type='INFO')

  @patch('gcpdiag.runbook.output.terminal_output.TerminalOutput.print_skipped')
  def test_add_skipped(self, mock_print_skipped):
    run_id = 'test_run'
    self.cli_interface.rm.reports[run_id] = report.Report(run_id, {})
    step = Step(uuid='skipped.step')
    step_result = report.StepResult(step)
    self.cli_interface.rm.add_step_result(run_id, step_result)
    self.cli_interface.add_skipped(run_id, self.resource, 'reason',
                                   step.execution_id)
    mock_print_skipped.assert_called_once()
    self.assertEqual(
        self.cli_interface.rm.reports[run_id].results[
            step.execution_id].results[0].status, 'skipped')

  @patch('gcpdiag.runbook.output.terminal_output.TerminalOutput.print_ok')
  def test_add_ok(self, mock_print_ok):
    run_id = 'test_run'
    self.cli_interface.rm.reports[run_id] = report.Report(run_id, {})
    step = Step(uuid='ok.step')
    step_result = report.StepResult(step)
    self.cli_interface.rm.add_step_result(run_id, step_result)
    self.cli_interface.add_ok(run_id, self.resource, step.execution_id,
                              'reason')
    mock_print_ok.assert_called_once()
    self.assertEqual(
        self.cli_interface.rm.reports[run_id].results[
            step.execution_id].results[0].status, 'ok')

  @patch('gcpdiag.runbook.output.terminal_output.TerminalOutput.prompt')
  @patch('gcpdiag.runbook.output.terminal_output.TerminalOutput.print_failed')
  def test_add_failed(self, mock_print_failed, mock_prompt):
    run_id = 'test_run'
    self.cli_interface.rm.reports[run_id] = report.Report(run_id, {})
    step = Step(uuid='failed.step')
    step_result = report.StepResult(step)
    self.cli_interface.rm.add_step_result(run_id, step_result)
    mock_prompt.return_value = report.constants.CONTINUE
    self.cli_interface.add_failed(run_id, self.resource, 'reason',
                                  'remediation', step.execution_id)
    mock_print_failed.assert_called_once()
    self.assertEqual(
        self.cli_interface.rm.reports[run_id].results[
            step.execution_id].results[0].status, 'failed')

  @patch('gcpdiag.runbook.output.terminal_output.TerminalOutput.prompt')
  @patch(
      'gcpdiag.runbook.output.terminal_output.TerminalOutput.print_uncertain')
  def test_add_uncertain(self, mock_print_uncertain, mock_prompt):
    run_id = 'test_run'
    self.cli_interface.rm.reports[run_id] = report.Report(run_id, {})
    step = Step(uuid='uncertain.step')
    step_result = report.StepResult(step)
    self.cli_interface.rm.add_step_result(run_id, step_result)
    mock_prompt.return_value = report.constants.CONTINUE
    self.cli_interface.add_uncertain(run_id, step.execution_id, self.resource,
                                     'reason', 'remediation')
    mock_print_uncertain.assert_called_once()
    self.assertEqual(
        self.cli_interface.rm.reports[run_id].results[
            step.execution_id].results[0].status, 'uncertain')

  @patch('gcpdiag.runbook.util.render_template')
  @patch('gcpdiag.runbook.output.terminal_output.TerminalOutput.info')
  def test_prepare_rca(self, mock_info, mock_render_template):
    run_id = 'test_run'
    self.cli_interface.rm.reports[run_id] = report.Report(run_id, {})
    step = Step(uuid='rca.step')
    step_result = report.StepResult(step)
    self.cli_interface.rm.add_step_result(run_id, step_result)
    mock_render_template.return_value = 'rca message'
    self.cli_interface.prepare_rca(run_id, self.resource, 'template::prefix',
                                   'suffix', step, {})
    mock_info.assert_called_with(message='rca message')
    self.assertEqual(
        self.cli_interface.rm.reports[run_id].results[
            step.execution_id].results[0].status, 'rca')

  @patch('importlib.import_module', side_effect=ImportError)
  @patch('logging.error')
  @patch('gcpdiag.runbook.output.terminal_output.TerminalOutput.info')
  @patch('gcpdiag.runbook.util.render_template')
  def test_prepare_rca_import_error(self, mock_render_template, mock_info,
                                    mock_logging_error,
                                    unused_mock_import_module):
    run_id = 'test_run'
    self.cli_interface.rm.reports[run_id] = report.Report(run_id, {})
    step = Step(uuid='rca.step')
    step_result = report.StepResult(step)
    self.cli_interface.rm.add_step_result(run_id, step_result)
    self.cli_interface.prepare_rca(run_id, self.resource, 'template::prefix',
                                   'suffix', step, {})
    # Check that logging.error was called with the exception
    mock_logging_error.assert_called_once()
    mock_info.assert_not_called()
    mock_render_template.assert_not_called()

  @patch('importlib.import_module')
  @patch('logging.error')
  @patch('gcpdiag.runbook.output.terminal_output.TerminalOutput.info')
  @patch('gcpdiag.runbook.util.render_template')
  def test_prepare_rca_attribute_error(self, mock_render_template, mock_info,
                                       mock_logging_error, mock_import_module):
    # Mock import_module to return a mock that raises AttributeError on __file__
    mock_import_module.return_value = Mock(spec_set=['some_attribute'])
    run_id = 'test_run'
    self.cli_interface.rm.reports[run_id] = report.Report(run_id, {})
    step = Step(uuid='rca.step')
    step_result = report.StepResult(step)
    self.cli_interface.rm.add_step_result(run_id, step_result)
    self.cli_interface.prepare_rca(run_id, self.resource, 'template::prefix',
                                   'suffix', step, {})
    # Verify the error was logged
    mock_logging_error.assert_called_once()
    self.assertEqual('failed to locate steps module %s',
                     mock_logging_error.call_args[0][0])
    mock_info.assert_not_called()
    mock_render_template.assert_not_called()
