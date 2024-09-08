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

import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock, patch

from gcpdiag import models, runbook
from gcpdiag.runbook.constants import StepType
from gcpdiag.runbook.gcp import flags
from gcpdiag.runbook.op import Operator


class TestDiagnosticEngine(unittest.TestCase):
  """Test Diagnostic Engine"""

  def setUp(self):
    self.mock_report_manager = Mock(spec=runbook.report.ReportManager)
    self.de: runbook.DiagnosticEngine = runbook.DiagnosticEngine(
        rm=self.mock_report_manager)

  def test_initialization_with_default_report_manager(self):
    engine = runbook.DiagnosticEngine()
    self.assertIsInstance(engine.rm, runbook.report.TerminalReportManager)

  def test_load_rule_invalid(self):
    with self.assertRaises(SystemExit) as cm:
      with self.assertRaises(runbook.exceptions.DiagnosticTreeNotFound):
        self.de.load_rule('invalid_rule_name')
    # Test program is exited with code 2 when invalid rule name is provided
    self.assertEqual(cm.exception.code, 2)

  #pylint: disable=protected-access
  def test_run_diagnostic_tree_missing_required_parameters(self):
    with self.assertRaises(SystemExit) as cm:
      dt = runbook.DiagnosticTree()
      dt.parameters = {'missing_param': {'required': True,}}
      self.de._check_required_paramaters(tree=dt, parameters=models.Parameter())
    self.assertEqual(cm.exception.code, 2)

  @patch('gcpdiag.runbook.DiagnosticEngine.run_step')
  def test_find_path_dfs_normal_operation(self, mock_run_step):
    op = Operator(interface=None)
    op.context = models.Context('')
    current_step = Mock(execution_id='1')
    current_step.steps = []
    visited = set()

    self.de.find_path_dfs(operator=op,
                          step=current_step,
                          executed_steps=visited)

    mock_run_step.assert_called()
    self.assertIn(current_step,
                  visited)  # Check if the current step was marked as visited

  @patch('gcpdiag.runbook.DiagnosticEngine.run_step')
  def test_find_path_dfs_finite_loop(self, mock_run_step):
    op = Operator(interface=None)
    op.context = models.Context('')
    current_step = Mock(execution_id='1', type=StepType.AUTOMATED)
    current_step.steps = [current_step]
    visited = set()

    self.de.find_path_dfs(operator=op,
                          step=current_step,
                          executed_steps=visited)

    mock_run_step.assert_called()
    self.assertIn(current_step, visited)

  @patch('gcpdiag.runbook.DiagnosticEngine.run_step')
  def test_find_path_all_child_step_executions(self, mock_run_step):
    op = Operator(interface=None)
    op.context = models.Context('')
    first_step = Mock(execution_id='1')
    intermidiate_step = Mock(execution_id='2')
    first_step.steps = [intermidiate_step]
    last_step = Mock(execution_id='3')
    last_step.steps = []
    intermidiate_step.steps = [last_step, last_step, last_step, last_step]
    visited = set()

    self.de.find_path_dfs(operator=op, step=first_step, executed_steps=visited)

    self.assertIn(first_step, visited)
    self.assertIn(intermidiate_step, visited)
    self.assertIn(last_step, visited)
    self.assertEqual(mock_run_step.call_count, 3)


class TestSetDefaultParameters(unittest.TestCase):
  """Test for Setting default date parameters"""

  def setUp(self):
    self.mock_report_manager = Mock(spec=runbook.report.ReportManager)
    self.de: runbook.DiagnosticEngine = runbook.DiagnosticEngine(
        rm=self.mock_report_manager)
    self.de.tree = Mock(parent=runbook.DiagnosticTree)
    self.de.tree.context = models.Context('project')

  def test_no_parameters_set(self):
    parameters = models.Parameter()
    self.de.tree.parameters = {}
    self.de.parse_parameters(tree=self.de.tree, parameters=parameters)
    self.assertIn(flags.END_TIME_UTC, parameters)
    self.assertIn(flags.START_TIME_UTC, parameters)
    end_time = parameters[flags.END_TIME_UTC]
    start_time = parameters[flags.START_TIME_UTC]

    # Assert end_time is recent and start_time is 8 hours before end_time
    self.assertTrue(isinstance(end_time, datetime))
    self.assertTrue(isinstance(start_time, datetime))
    self.assertAlmostEqual(end_time - start_time,
                           timedelta(hours=8),
                           delta=timedelta(seconds=10))

  def test_end_time_provided_in_rfc3339(self):
    end_t_str = '2024-03-20T15:00:00Z'
    parameters = models.Parameter()
    parameters[flags.END_TIME_UTC] = end_t_str
    self.de.tree.parameters = {}
    self.de.parse_parameters(tree=self.de.tree, parameters=parameters)
    end_time = parameters[flags.END_TIME_UTC]
    start_time = parameters[flags.START_TIME_UTC]

    exp_end_time = datetime.strptime(
        end_t_str, '%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=timezone.utc)
    self.assertEqual(end_time, exp_end_time)
    self.assertEqual(start_time, exp_end_time - timedelta(hours=8))

  def test_only_start_time_provided_in_rfc3339(self):
    start_t_str = '2024-03-20T07:00:00Z'
    parameters = models.Parameter()
    parameters[flags.START_TIME_UTC] = start_t_str
    self.de.tree.parameters = {}
    self.de.parse_parameters(tree=self.de.tree, parameters=parameters)
    start_time = parameters[flags.START_TIME_UTC]
    end_time = parameters[flags.END_TIME_UTC]

    exp_start_time = datetime.strptime(
        start_t_str, '%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=timezone.utc)
    self.assertEqual(start_time, exp_start_time)
    self.assertTrue(isinstance(end_time, datetime))

  def test_both_times_provided_in_rfc3339(self):
    start_time_str = '2024-03-20T07:00:00Z'
    end_time_str = '2024-03-20T15:00:00Z'
    self.de.tree.parameters = {}
    parameters = models.Parameter()
    parameters[flags.START_TIME_UTC] = start_time_str
    parameters[flags.END_TIME_UTC] = end_time_str

    self.de.parse_parameters(self.de.tree, parameters)
    start_time = parameters[flags.START_TIME_UTC]
    end_time = parameters[flags.END_TIME_UTC]

    expected_start_time = datetime.strptime(
        start_time_str, '%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=timezone.utc)
    expected_end_time = datetime.strptime(
        end_time_str, '%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=timezone.utc)
    self.assertEqual(start_time, expected_start_time)
    self.assertEqual(end_time, expected_end_time)

  def test_times_provided_in_epoch_format(self):
    start_time_epoch = '1601481600'  # 2020-09-30 16:00:00 UTC
    end_time_epoch = '1601485200'  # 2020-09-30 17:00:00 UTC
    parameters = models.Parameter()
    parameters[flags.START_TIME_UTC] = start_time_epoch
    parameters[flags.END_TIME_UTC] = end_time_epoch
    self.de.tree.parameters = {}
    self.de.parse_parameters(tree=self.de.tree, parameters=parameters)
    start_time = parameters[flags.START_TIME_UTC]
    end_time = parameters[flags.END_TIME_UTC]

    expected_start_time = datetime.fromtimestamp(float(start_time_epoch),
                                                 tz=timezone.utc)
    expected_end_time = datetime.fromtimestamp(float(end_time_epoch),
                                               tz=timezone.utc)
    self.assertEqual(start_time, expected_start_time)
    self.assertEqual(end_time, expected_end_time)

  def test_invalid_format_provided(self):
    start_time_invalid = 'invalid_start_time'
    end_time_invalid = 'invalid_end_time'
    parameters = models.Parameter()
    parameters[flags.START_TIME_UTC] = start_time_invalid
    parameters[flags.END_TIME_UTC] = end_time_invalid
    self.de.tree.parameters = {}
    with self.assertRaises(ValueError):
      self.de.parse_parameters(tree=self.de.tree, parameters=parameters)
