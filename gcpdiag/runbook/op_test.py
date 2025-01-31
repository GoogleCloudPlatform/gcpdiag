# Copyright 2024 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the 'License');
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an 'AS IS' BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
'''Test Operator methods'''

import unittest
from functools import wraps

from gcpdiag.runbook import Step, op, report


def with_operator_context(test_method):
  """Decorator to set up operator context for op_test test methods."""

  @wraps(test_method)
  def wrapper(self):
    test_operator = op.Operator(interface=report.InteractionInterface(
        kind='cli'))
    test_operator.set_run_id('test_run_for_' + test_method.__name__)
    test_operator.interface.rm = report.TerminalReportManager()
    test_report = report.Report(run_id=test_operator.run_id, parameters={})
    test_operator.interface.rm.reports[test_operator.run_id] = test_report
    test_step = ok_step
    test_operator.set_step(test_step)

    test_report.results[ok_step.execution_id] = ok_step
    test_report.results[failed_step.execution_id] = failed_step
    test_report.results[uncertain_step.execution_id] = uncertain_step
    test_report.results[skipped_step.execution_id] = skipped_step

    self.test_operator = test_operator

    with op.operator_context(test_operator):
      return test_method(
          self)  # Execute the actual test method within the context

  return wrapper


ok_step_eval = report.ResourceEvaluation(resource=None,
                                         status='ok',
                                         reason='TestReason',
                                         remediation='TestRemediation')
failed_step_eval = report.ResourceEvaluation(resource=None,
                                             reason='TestReason',
                                             remediation='TestRemediation',
                                             status='failed')
uncertain_step_eval = report.ResourceEvaluation(resource=None,
                                                reason='TestReason',
                                                remediation='TestRemediation',
                                                status='uncertain')
skipped_step_eval = report.ResourceEvaluation(resource=None,
                                              reason='TestReason',
                                              remediation='TestRemediation',
                                              status='skipped')
ok_step = report.StepResult(step=Step(uuid='ok.step'))
ok_step.results.append(ok_step_eval)
failed_step = report.StepResult(step=Step(uuid='failed.step'))
failed_step.results.append(failed_step_eval)
uncertain_step = report.StepResult(step=Step(uuid='uncertain.step'))
uncertain_step.results.append(uncertain_step_eval)
skipped_step = report.StepResult(step=Step(uuid='skipped.step'))
skipped_step.results.append(skipped_step_eval)

# This global operator is only used for creating step results and should not interfere with
# thread-local tests.
operator = op.Operator(interface=report.InteractionInterface(kind='cli'))
operator.set_run_id('test')
operator.interface.rm = report.TerminalReportManager()
operator.interface.rm.reports['test'] = report.Report(run_id='test',
                                                      parameters={})
operator.interface.rm.reports['test'].results[ok_step.execution_id] = ok_step
operator.interface.rm.reports['test'].results[
    failed_step.execution_id] = failed_step
operator.interface.rm.reports['test'].results[
    uncertain_step.execution_id] = uncertain_step
operator.interface.rm.reports['test'].results[
    skipped_step.execution_id] = skipped_step

operator.set_step(ok_step)


class OperatorTest(unittest.TestCase):
  '''Test Report Manager'''

  @with_operator_context
  def test_positive_step_overall_status_case(self):
    self.assertTrue(op.step_ok('gcpdiag.runbook.Step.ok.step'))
    self.assertTrue(op.step_failed('gcpdiag.runbook.Step.failed.step'))
    self.assertTrue(op.step_uncertain('gcpdiag.runbook.Step.uncertain.step'))
    self.assertTrue(op.step_skipped('gcpdiag.runbook.Step.skipped.step'))
    self.assertTrue(op.step_unexecuted('gcpdiag.runbook.Step.random.step'))

  @with_operator_context
  def test_negative_step_overall_status_case(self):
    self.assertFalse(op.step_ok('gcpdiag.runbook.Step.failed.step'))
    self.assertFalse(op.step_failed('gcpdiag.runbook.Step.ok.step'))
    self.assertFalse(op.step_uncertain('gcpdiag.runbook.Step.ok.step'))
    self.assertFalse(op.step_skipped('gcpdiag.runbook.Step.failed.step'))
    self.assertFalse(op.step_unexecuted('gcpdiag.runbook.Step.ok.step'))

  @with_operator_context
  def test_get_and_put_parameters(self):
    self.test_operator.parameters = {'test_key': 'test_value'}
    self.assertEqual(op.get('test_key'), 'test_value')
    self.assertEqual(op.get('unknown_key', 'default_value'), 'default_value')
    op.put('new_key', 'new_value')
    self.assertEqual(self.test_operator.parameters['new_key'], 'new_value')

  @with_operator_context
  def test_get_step_outcome(self):
    overall_status, totals = op.get_step_outcome(ok_step.execution_id)
    self.assertEqual(overall_status, 'ok')
    self.assertEqual(totals, {'ok': 1})

    overall_status, totals = op.get_step_outcome('unknown_step')
    self.assertIsNone(overall_status)
    self.assertEqual(totals, {})

  @with_operator_context
  def test_add_and_get_metadata(self):
    op.add_metadata('metadata_key_one', 'test_value_one')
    op.add_metadata('metadata_key_two', 'test_value_two')
    value = op.get_metadata('metadata_key_one')
    self.assertEqual(value, 'test_value_one')

    all_metadata = op.get_all_metadata()
    self.assertEqual(2, len(all_metadata))
    self.assertEqual(op.get_all_metadata()['metadata_key_two'],
                     'test_value_two')

  @with_operator_context
  def test_add_info_metadata(self):
    info = ['info1', 'info2', 'info3']
    for i in info:
      op.info(i)
    step_report = self.test_operator.interface.rm.reports[
        self.test_operator.run_id].results.get(ok_step.execution_id)
    self.assertEqual(info, step_report.info)
