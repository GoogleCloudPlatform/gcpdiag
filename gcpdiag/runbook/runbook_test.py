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
from unittest.mock import Mock, patch

from gcpdiag import models, runbook
from gcpdiag.runbook.constants import StepType


class TestDiagnosticEngine(unittest.TestCase):
  """Test Diagnostic Engine"""

  def setUp(self):
    self.mock_report_manager = Mock(spec=runbook.report.ReportManager)
    self.de: runbook.DiagnosticEngine = runbook.DiagnosticEngine(
        rm=self.mock_report_manager)

  def test_initialization_with_default_report_manager(self):
    engine = runbook.DiagnosticEngine()
    self.assertIsInstance(engine.rm, runbook.report.TerminalReportManager)

  def test_load_rule_valid(self):
    mock_dt = Mock(parent=runbook.DiagnosticTree)
    runbook.DiagnosticTreeRegister['product/test-tree'] = mock_dt
    self.de.load_rule('product/test-tree')
    # pylint: disable=protected-access
    self.assertEqual(self.de.dt, mock_dt)

  def test_load_rule_invalid(self):
    with self.assertRaises(SystemExit) as cm:
      with self.assertRaises(runbook.exceptions.DiagnosticTreeNotFound):
        self.de.load_rule('invalid_rule_name')
    # Test program is exited with code 2 when invalid rule name is provided
    self.assertEqual(cm.exception.code, 2)

  #pylint: disable=protected-access
  def test_run_diagnostic_tree_missing_parameters(self):
    with self.assertRaises(SystemExit) as cm:
      context = models.Context('project_id', parameters={})
      dt = runbook.DiagnosticTree(context=context)
      dt.req_params = {'missing_param': None}
      self.de._check_required_paramaters(dt)
    self.assertEqual(cm.exception.code, 2)

  @patch('gcpdiag.runbook.DiagnosticEngine.run_step')
  def test_find_path_dfs_normal_operation(self, mock_run_step):
    context = models.Context('product_id')
    current_step = Mock(run_id='1')
    current_step.steps = []
    visited = set()

    self.de.find_path_dfs(context=context,
                          interface=self.de.interface,
                          step=current_step,
                          executed_steps=visited)

    mock_run_step.assert_called()
    self.assertIn(current_step,
                  visited)  # Check if the current step was marked as visited

  @patch('gcpdiag.runbook.DiagnosticEngine.run_step')
  def test_find_path_dfs_finite_loop(self, mock_run_step):
    context = models.Context('product_id')
    current_step = Mock(run_id='1', type=StepType.AUTOMATED)
    current_step.steps = [current_step]
    visited = set()

    self.de.find_path_dfs(context=context,
                          step=current_step,
                          executed_steps=visited)

    mock_run_step.assert_called()
    self.assertIn(current_step, visited)

  @patch('gcpdiag.runbook.DiagnosticEngine.run_step')
  def test_find_path_all_child_step_executions(self, mock_run_step):
    context = models.Context('product_id')
    first_step = Mock(run_id='1')
    intermidiate_step = Mock(run_id='2')
    first_step.steps = [intermidiate_step]
    last_step = Mock(run_id='3')
    last_step.steps = []
    intermidiate_step.steps = [last_step, last_step, last_step, last_step]
    visited = set()

    self.de.find_path_dfs(context=context,
                          step=first_step,
                          executed_steps=visited)

    self.assertIn(first_step, visited)
    self.assertIn(intermidiate_step, visited)
    self.assertIn(last_step, visited)
    self.assertEqual(mock_run_step.call_count, 3)
