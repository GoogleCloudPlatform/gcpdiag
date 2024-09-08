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

from gcpdiag.runbook import Step, op, report

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

op.operator = op.Operator(interface=report.InteractionInterface())
op.operator.interface.rm = report.TerminalReportManager()
op.operator.interface.rm.results[ok_step.execution_id] = ok_step
op.operator.interface.rm.results[failed_step.execution_id] = failed_step
op.operator.interface.rm.results[uncertain_step.execution_id] = uncertain_step
op.operator.interface.rm.results[skipped_step.execution_id] = skipped_step

op.operator.set_step(ok_step)


class OperatorTest(unittest.TestCase):
  '''Test Report Manager'''

  def test_positive_step_overall_status_case(self):
    self.assertTrue(op.step_ok('gcpdiag.runbook.Step.ok.step'))
    self.assertTrue(op.step_failed('gcpdiag.runbook.Step.failed.step'))
    self.assertTrue(op.step_uncertain('gcpdiag.runbook.Step.uncertain.step'))
    self.assertTrue(op.step_skipped('gcpdiag.runbook.Step.skipped.step'))
    self.assertTrue(op.step_unexecuted('gcpdiag.runbook.Step.random.step'))

  def test_negative_step_overall_status_case(self):
    self.assertFalse(op.step_ok('gcpdiag.runbook.Step.failed.step'))
    self.assertFalse(op.step_failed('gcpdiag.runbook.Step.ok.step'))
    self.assertFalse(op.step_uncertain('gcpdiag.runbook.Step.ok.step'))
    self.assertFalse(op.step_skipped('gcpdiag.runbook.Step.failed.step'))
    self.assertFalse(op.step_unexecuted('gcpdiag.runbook.Step.ok.step'))

  def test_get_and_put_parameters(self):
    op.operator.parameters = {'test_key': 'test_value'}
    self.assertEqual(op.get('test_key'), 'test_value')
    self.assertEqual(op.get('unknown_key', 'default_value'), 'default_value')
    op.put('new_key', 'new_value')
    self.assertEqual(op.operator.parameters['new_key'], 'new_value')

  def test_get_step_outcome(self):
    overall_status, totals = op.get_step_outcome(ok_step.execution_id)
    self.assertEqual(overall_status, 'ok')
    self.assertEqual(totals, {'ok': 1})

    overall_status, totals = op.get_step_outcome('unknown_step')
    self.assertIsNone(overall_status)
    self.assertEqual(totals, {})

  def test_add_and_get_metadata(self):
    op.add_metadata('metadata_key_one', 'test_value_one')
    op.add_metadata('metadata_key_two', 'test_value_two')
    value = op.get_metadata('metadata_key_one')
    self.assertEqual(value, 'test_value_one')

    all_metadata = op.get_all_metadata()
    self.assertEqual(2, len(all_metadata))
    self.assertEqual(op.get_all_metadata()['metadata_key_two'],
                     'test_value_two')

  def test_add_info_metadata(self):
    info = ['info1', 'info2', 'info3']
    for i in info:
      op.info(i)
    step_report = op.operator.interface.rm.results.get(ok_step.execution_id)
    self.assertEqual(info, step_report.info)
