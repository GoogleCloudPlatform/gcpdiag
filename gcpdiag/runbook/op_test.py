# Copyright 2024 Google LLC
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
"""Test Operator methods"""

import unittest

from gcpdiag.models import Context
from gcpdiag.runbook import op, report

ok_step = report.StepResult(status='ok',
                            resource=None,
                            step='ok.step',
                            reason='TestReason',
                            remediation='TestRemediation',
                            remediation_skipped=True,
                            prompt_response=None)
failed_step = report.StepResult(status='failed',
                                resource=None,
                                step='failed.step',
                                reason='TestReason',
                                remediation='TestRemediation',
                                remediation_skipped=True,
                                prompt_response=None)
uncertain_step = report.StepResult(status='uncertain',
                                   resource=None,
                                   step='uncertain.step',
                                   reason='TestReason',
                                   remediation='TestRemediation',
                                   remediation_skipped=True,
                                   prompt_response=None)
skipped_step = report.StepResult(status='skipped',
                                 resource=None,
                                 step='skipped.step',
                                 reason='TestReason',
                                 remediation='TestRemediation',
                                 remediation_skipped=True,
                                 prompt_response=None)


class OperatorTest(unittest.TestCase):
  """Test Report Manager"""

  def setUp(self):
    op.operator = op.Operator(Context('test-project'),
                              report.InteractionInterface())
    op.operator.interface.rm = report.TerminalReportManager()
    op.operator.interface.rm.results[ok_step.step] = ok_step
    op.operator.interface.rm.results[failed_step.step] = failed_step
    op.operator.interface.rm.results[uncertain_step.step] = uncertain_step
    op.operator.interface.rm.results[skipped_step.step] = skipped_step

  def test_postive_step_overall_status_case(self):
    self.assertTrue(op.step_ok('ok.step'))
    self.assertTrue(op.step_failed('failed.step'))
    self.assertTrue(op.step_uncertain('uncertain.step'))
    self.assertTrue(op.step_skipped('skipped.step'))
    self.assertTrue(op.step_unexecuted('random.step'))

  def test_negative_step_overall_status_case(self):
    self.assertFalse(op.step_ok('failed.step'))
    self.assertFalse(op.step_failed('ok.step'))
    self.assertFalse(op.step_uncertain('ok.step'))
    self.assertFalse(op.step_skipped('failed.step'))
    self.assertFalse(op.step_unexecuted('ok.step'))
