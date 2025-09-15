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
from unittest.mock import ANY, Mock, call, patch

from gcpdiag import models, runbook
from gcpdiag.runbook import constants, exceptions
from gcpdiag.runbook.gcp import flags
from gcpdiag.runbook.op import Operator


class LegacyParamHandler(runbook.DiagnosticTree):
  """test runbook"""
  parameters = {
      'new_param': {
          'required': True
      },
      'deprecated_param': {
          'new_parameter': 'new_param',
          'deprecated': True
      }
  }

  # pylint: disable=unused-argument
  def legacy_parameter_handler(self, parameters):
    if 'deprecated_param' in parameters:
      parameters['new_param'] = True
      del parameters['deprecated_param']


class TestDiagnosticEngine(unittest.TestCase):
  """Test Diagnostic Engine"""

  def setUp(self):
    self.mock_report_manager = Mock(spec=runbook.report.ReportManager)
    self.mock_report_manager.reports = {}
    self.de = runbook.DiagnosticEngine()
    step = runbook.Step
    step.parameters = {}
    self.de.add_task((runbook.Bundle(), {}))
    self.de.add_task((runbook.DiagnosticTree(), {}))

  # pylint: disable=protected-access
  def test_run_diagnostic_tree_missing_required_parameters(self):
    with self.assertRaises(exceptions.MissingParameterError) as cm:
      dt = runbook.DiagnosticTree()
      dt.parameters = {
          'missing_param': {
              'required': True,
              'help': 'Missing parameter help'
          },
      }
      self.de._check_required_paramaters(parameter_def=dt.parameters,
                                         caller_args=models.Parameter())
    self.assertEqual(cm.exception.missing_parameters_list, ['missing_param'])
    self.assertIn('Missing 1 required parameter', str(cm.exception))
    self.assertIn('Parameter Explanation: Missing parameter help',
                  str(cm.exception))
    self.assertIn('-p missing_param=value', str(cm.exception))

  @patch('logging.warning')
  def test_run_diagnostic_tree_deprecated_parameters(self, mock_logging_error):
    parameters = {
        'deprecated_param': {
            'deprecated': True,
            'new_parameter': 'new_value'
        }
    }
    result = self.de._check_deprecated_paramaters(
        parameter_def=parameters,
        caller_args=models.Parameter({'deprecated_param': 'val'}))
    assert 'Deprecated parameters:\ndeprecated_param. Use: new_value=value' in result
    mock_logging_error.assert_called_once()

  # pylint: disable=protected-access
  def test_both_new_and_deprecated_missing(self):
    with self.assertRaises(exceptions.MissingParameterError):
      dt = LegacyParamHandler()
      user_supplied = models.Parameter({'random': 'value'})
      dt.legacy_parameter_handler(user_supplied)
      self.de._check_required_paramaters(parameter_def=dt.parameters,
                                         caller_args=user_supplied)

  # pylint: disable=protected-access
  def test_backward_compatibility_for_deprecated_params(self):
    dt = LegacyParamHandler()
    user_supplied_param = models.Parameter({'deprecated_param': 'used_by_user'})
    dt.legacy_parameter_handler(user_supplied_param)
    self.de._check_required_paramaters(parameter_def=dt.parameters,
                                       caller_args=user_supplied_param)

  @patch('gcpdiag.runbook.DiagnosticEngine.run_step')
  def test_find_path_dfs_normal_operation(self, mock_run_step):
    op = Operator(interface=None)
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
    current_step = Mock(execution_id='1', type=constants.StepType.AUTOMATED)
    current_step.steps = [current_step]
    visited = set()

    self.de.find_path_dfs(operator=op,
                          step=current_step,
                          executed_steps=visited)

    mock_run_step.assert_called()
    self.assertIn(current_step, visited)

  @patch('gcpdiag.runbook.DiagnosticEngine.run_step')
  def test_find_path_dfs_dynamically_added_child(self, mock_run_step):
    """Test that find_path_dfs executes dynamically added step as child."""
    op = Operator(interface=None)
    step_root = Mock(execution_id='root_step')
    step_initial_a = Mock(execution_id='initial_child_A', steps=[])
    step_initial_a._was_initially_defined = True
    step_initial_b = Mock(execution_id='initial_child_B', steps=[])
    step_initial_b._was_initially_defined = True
    step_dynamic_b = Mock(execution_id='dynamic_child_B', steps=[])
    del step_dynamic_b._was_initially_defined

    step_root.steps = [step_initial_a]
    step_initial_a.steps = [step_initial_b, step_dynamic_b]
    mock_run_step.return_value = None
    executed_steps = set()
    self.de.find_path_dfs(
        step=step_root,
        operator=op,
        executed_steps=executed_steps,
    )
    expected_run_step_calls = [
        call(step=step_root, operator=op),
        call(step=step_initial_a, operator=op),
        call(step=step_dynamic_b, operator=op),
        call(step=step_initial_b, operator=op),
    ]

    mock_run_step.assert_has_calls(expected_run_step_calls, any_order=False)

    self.assertIn(step_root, executed_steps)
    self.assertIn(step_initial_a, executed_steps)
    self.assertIn(step_dynamic_b, executed_steps)
    self.assertEqual(len(executed_steps), 4)

  @patch('gcpdiag.runbook.DiagnosticEngine.run_step')
  def test_find_path_dfs_dynamic_end_step_stops_execution(self, mock_run_step):
    op_instance = Operator(interface=None)
    root_step = Mock(execution_id='root')
    intermediate_step = Mock(execution_id='intermediate')
    finalize_step = Mock(execution_id='finalize_investigation',
                         type=constants.StepType.END)
    should_not_run_step = Mock(execution_id='should_not_run')
    should_not_run_step._was_initially_defined = True
    root_step.steps = [intermediate_step, should_not_run_step]
    intermediate_step.steps = [finalize_step]

    def side_effect_for_run_step(step, operator):  # pylint: disable=unused-argument
      if step.type == constants.StepType.END:
        # This step signals to stop the investigation
        return constants.FINALIZE_INVESTIGATION
      # Other steps just continue normally
      return None

    mock_run_step.side_effect = side_effect_for_run_step

    executed_steps_tracker = set()
    self.de.find_path_dfs(
        step=root_step,
        operator=op_instance,
        executed_steps=executed_steps_tracker,
    )

    expected_calls = [
        call(step=root_step, operator=op_instance),
        call(step=intermediate_step, operator=op_instance),
        call(step=finalize_step, operator=op_instance),
    ]
    mock_run_step.assert_has_calls(expected_calls, any_order=False)
    self.assertNotIn(
        call(step=should_not_run_step, operator=op_instance),
        mock_run_step.call_args_list,
    )
    self.assertEqual(mock_run_step.call_count, 3)
    self.assertIn(root_step, executed_steps_tracker)
    self.assertIn(intermediate_step, executed_steps_tracker)
    self.assertIn(finalize_step, executed_steps_tracker)
    self.assertNotIn(should_not_run_step, executed_steps_tracker)
    self.assertTrue(self.de.finalize)

  @patch('gcpdiag.runbook.DiagnosticEngine.run_step')
  def test_find_path_all_child_step_executions(self, mock_run_step):
    op = Operator(interface=None)
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

  @patch('gcpdiag.runbook.op.Operator')
  @patch('gcpdiag.runbook.DiagnosticEngine.run_step')
  def test_gateway_step_in_bundle(self, mock_run_step, mock_operator_class):
    """Dedicated test to ensure gateway steps in bundles execute child steps and report results."""
    self.de.interface = Mock()
    self.de.interface.rm = self.mock_report_manager
    mock_op_instance = Mock()
    mock_operator_class.return_value = mock_op_instance

    # Create mock steps to track execution
    mock_child_execute = Mock()
    mock_gateway_execute = Mock()

    class MockChildStep(runbook.Step):
      template = 'mock_child'

      def execute(self, op):
        """Executes mock child step."""
        mock_child_execute()
        op.add_ok(resource=Mock(spec=models.Resource),
                  reason='Child step executed')

    class MockGatewayStep(runbook.Gateway):
      template = 'mock_gateway'

      def execute(self, op):  # pylint: disable=unused-argument
        """Executes mock gateway step."""
        mock_gateway_execute()
        self.add_child(MockChildStep())

    bundle = runbook.Bundle()
    bundle.run_id = 'test_bundle_run'
    bundle.parameter = models.Parameter({})
    bundle.steps = [MockGatewayStep]

    def run_step_side_effect(step, operator):
      # StartStep is an internal step and its execute method doesn't take any
      # arguments. The real run_step handles this, so our mock should too.
      if isinstance(step, runbook.StartStep):
        step.execute()
      else:
        step.execute(operator)

    mock_run_step.side_effect = run_step_side_effect
    self.de.run_bundle(bundle=bundle)

    # Assert that the gateway and the dynamically added child were executed
    mock_gateway_execute.assert_called_once()
    mock_child_execute.assert_called_once()
    mock_op_instance.add_ok.assert_called_once_with(
        resource=ANY, reason='Child step executed')

  @patch('gcpdiag.runbook.DiagnosticEngine.run_bundle')
  @patch('gcpdiag.runbook.DiagnosticEngine.run_diagnostic_tree')
  def test_run_operation(self, mock_run_bundle, mock_run_diagnostic_tree):

    self.de.run()
    assert mock_run_bundle.called
    assert mock_run_diagnostic_tree.called

  @patch('gcpdiag.runbook.DiagnosticEngine.run_step')
  def test_run_bundles(self, mock_run_step):
    bundle = runbook.Bundle()
    param = {
        'param_one': 'test',
        'param_two': True,
        'param_three': datetime.now()
    }
    bundle.parameter = models.Parameter(param)
    bundle.steps.append(runbook.Step)
    self.de.run_bundle(bundle=bundle)
    _, kwargs = mock_run_step.call_args
    assert mock_run_step.called
    assert isinstance(kwargs['step'], runbook.Step)
    assert kwargs['step'].param_one == param['param_one']
    assert kwargs['step'].param_two == param['param_two']
    assert kwargs['step'].param_three == param['param_three']

  def test_run_diagnostic_tree_missing_legacy_handler(self):
    with self.assertRaises(TypeError) as context:
      # pylint: disable=unused-variable
      class MissingLegacyHandler(runbook.DiagnosticTree):
        parameters = {
            'deprecated_param': {
                'type': str,
                'help': 'Deprecated parameter',
                'deprecated': True,  # triggers Type error because of this field
                'new_parameter': 'new_param'
            }
        }

    self.assertIn((
        'does not implement legacy_parameter_handler(). Implement this method to handle '
        'backward compatibility for deprecated parameters.'),
                  str(context.exception))


class TestSetDefaultParameters(unittest.TestCase):
  """Test for Setting default date parameters"""

  def setUp(self):
    self.de = runbook.DiagnosticEngine()
    self.de.add_task((Mock(parent=runbook.DiagnosticTree), {}))

  def test_no_parameters_set(self):
    parameters = models.Parameter()
    self.de.parse_parameters(parameter_def={}, caller_args=parameters)
    self.assertIn(flags.END_TIME, parameters)
    self.assertIn(flags.START_TIME, parameters)
    end_time = parameters[flags.END_TIME]
    start_time = parameters[flags.START_TIME]

    # Assert end_time is recent and start_time is 8 hours before end_time
    self.assertTrue(isinstance(end_time, datetime))
    self.assertTrue(isinstance(start_time, datetime))
    self.assertAlmostEqual(end_time - start_time,
                           timedelta(hours=8),
                           delta=timedelta(seconds=10))

  def test_end_time_provided_in_rfc3339(self):
    end_t_str = '2024-03-20T15:00:00Z'
    parameters = models.Parameter()
    parameters[flags.END_TIME] = end_t_str
    self.de.parse_parameters(parameter_def={}, caller_args=parameters)
    end_time = parameters[flags.END_TIME]
    start_time = parameters[flags.START_TIME]

    exp_end_time = datetime.strptime(
        end_t_str, '%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=timezone.utc)
    self.assertEqual(end_time, exp_end_time)
    self.assertEqual(start_time, exp_end_time - timedelta(hours=8))

  def test_only_start_time_provided_in_rfc3339(self):
    start_t_str = '2024-03-20T07:00:00Z'
    parameters = models.Parameter()
    parameters[flags.START_TIME] = start_t_str
    self.de.parse_parameters(parameter_def={}, caller_args=parameters)
    start_time = parameters[flags.START_TIME]
    end_time = parameters[flags.END_TIME]

    exp_start_time = datetime.strptime(
        start_t_str, '%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=timezone.utc)
    self.assertEqual(start_time, exp_start_time)
    self.assertTrue(isinstance(end_time, datetime))

  def test_both_times_provided_in_rfc3339(self):
    start_time_str = '2024-03-20T07:00:00Z'
    end_time_str = '2024-03-20T15:00:00Z'
    parameters = models.Parameter()
    parameters[flags.START_TIME] = start_time_str
    parameters[flags.END_TIME] = end_time_str

    self.de.parse_parameters(parameter_def={}, caller_args=parameters)
    start_time = parameters[flags.START_TIME]
    end_time = parameters[flags.END_TIME]

    expected_start_time = datetime.strptime(
        start_time_str, '%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=timezone.utc)
    expected_end_time = datetime.strptime(
        end_time_str, '%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=timezone.utc)
    self.assertEqual(start_time, expected_start_time)
    self.assertEqual(end_time, expected_end_time)

  def test_start_time_provided_in_utc_format(self):
    start_time_str = '2024-07-20'
    self.de.parameters = {}
    parameters = models.Parameter()
    parameters[flags.START_TIME] = start_time_str

    self.de.parse_parameters(self.de.parameters, parameters)
    start_time = parameters[flags.START_TIME]
    end_time = parameters[flags.END_TIME]

    self.assertEqual(str(start_time), '2024-07-20 00:00:00+00:00')
    self.assertTrue(str(end_time), isinstance(end_time, datetime))

  def test_end_time_provided_in_utc_format(self):
    end_time_str = '2024-07-20'
    self.de.parameters = {}
    parameters = models.Parameter()
    parameters[flags.END_TIME] = end_time_str

    self.de.parse_parameters(self.de.parameters, parameters)
    start_time = parameters[flags.START_TIME]
    end_time = parameters[flags.END_TIME]

    self.assertEqual(str(start_time), '2024-07-19 16:00:00+00:00')
    self.assertEqual(str(end_time), '2024-07-20 00:00:00+00:00')

  def test_both_times_provided_in_utc_format(self):
    start_time_str = '2024-07-20'
    end_time_str = '2024-08-25'
    self.de.parameters = {}
    parameters = models.Parameter()
    parameters[flags.START_TIME] = start_time_str
    parameters[flags.END_TIME] = end_time_str

    self.de.parse_parameters(self.de.parameters, parameters)
    start_time = parameters[flags.START_TIME]
    end_time = parameters[flags.END_TIME]

    self.assertEqual(str(start_time), '2024-07-20 00:00:00+00:00')
    self.assertEqual(str(end_time), '2024-08-25 00:00:00+00:00')

  def test_both_times_provided_in_non_utc_format(self):
    start_time_str = '2024-07-20 00:00:00'
    # '2024-07-20T12:00:00-05:00'   12 PM EST (UTC-5)
    end_time_str = '2024-08-25 00:00:00'
    # '2024-08-25T15:00:00-07:00'     3 PM PDT (UTC-7)

    self.de.parameters = {}
    parameters = models.Parameter()

    parameters[flags.START_TIME] = start_time_str
    parameters[flags.END_TIME] = end_time_str

    self.de.parse_parameters(self.de.parameters, parameters)
    start_time = parameters[flags.START_TIME]
    end_time = parameters[flags.END_TIME]

    # Convert expected UTC times for the test case
    expected_start_time = '2024-07-20 00:00:00+00:00'
    # '2024-07-20 17:00:00+00:00'   12 PM EST is 5 PM UTC
    expected_end_time = '2024-08-25 00:00:00+00:00'
    # '2024-08-25 22:00:00+00:00'     3 PM PDT is 10 PM UTC

    self.assertEqual(str(start_time), expected_start_time)
    self.assertEqual(str(end_time), expected_end_time)

  def test_times_provided_in_epoch_format(self):
    start_time_epoch = '1601481600'  # 2020-09-30 16:00:00 UTC
    end_time_epoch = '1601485200'  # 2020-09-30 17:00:00 UTC
    parameters = models.Parameter()
    parameters[flags.START_TIME] = start_time_epoch
    parameters[flags.END_TIME] = end_time_epoch
    self.de.parse_parameters(parameter_def={}, caller_args=parameters)
    start_time = parameters[flags.START_TIME]
    end_time = parameters[flags.END_TIME]

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
    parameters[flags.START_TIME] = start_time_invalid
    parameters[flags.END_TIME] = end_time_invalid
    with self.assertRaises(ValueError):
      self.de.parse_parameters(parameter_def={}, caller_args=parameters)


class TestMetaStepRegistry(unittest.TestCase):
  """Test for meta step registry."""

  def setUp(self):
    # Clear the registry before each test
    runbook.StepRegistry.clear()

  def test_register_step_subclass(self):

    class MyStep(runbook.Step):
      pass

    self.assertIn(MyStep.id, runbook.StepRegistry)
    self.assertIs(runbook.StepRegistry[MyStep.id], MyStep)

  def test_register_gateway_subclass(self):

    class MyGateway(runbook.Gateway):
      pass

    self.assertIn(MyGateway.id, runbook.StepRegistry)
    self.assertIs(runbook.StepRegistry[MyGateway.id], MyGateway)

  def test_register_composite_step_subclass(self):

    class MyCompositeStep(runbook.CompositeStep):
      pass

    self.assertIn(MyCompositeStep.id, runbook.StepRegistry)
    self.assertIs(runbook.StepRegistry[MyCompositeStep.id], MyCompositeStep)

  def test_dont_register_base_classes(self):
    self.assertNotIn(runbook.Step.id, runbook.StepRegistry)
    self.assertNotIn(runbook.Gateway.id, runbook.StepRegistry)

  def test_dont_register_other_classes(self):

    class NotAStep:
      pass

    not_a_step_id = '.'.join([NotAStep.__module__, NotAStep.__name__])
    self.assertNotIn(not_a_step_id, runbook.StepRegistry)
