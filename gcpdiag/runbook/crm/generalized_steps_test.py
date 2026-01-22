# Copyright 2026 Google LLC
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
"""Test class for crm.generalized_steps."""

import datetime
import unittest
from unittest import mock

from gcpdiag.queries import apis_stub
from gcpdiag.runbook import op
from gcpdiag.runbook.crm import generalized_steps
from gcpdiag.runbook.iam import flags

DUMMY_PROJECT_ID = 'gcpdiag-fw-policy-aaaa'


class MockMessage:
  """Mock messages for testing."""

  def get_msg(self, key, **kwargs):
    del kwargs
    return f'{key}'


class GeneralizedStepsTestBase(unittest.TestCase):
  """Base class for CRM generalized step tests."""

  def setUp(self):
    super().setUp()
    # 1. Patch get_api with the stub.
    self.enterContext(
        mock.patch('gcpdiag.queries.apis.get_api', new=apis_stub.get_api_stub))
    # 2. Create a mock interface to capture outputs
    self.mock_interface = mock.create_autospec(op.InteractionInterface,
                                               instance=True)
    self.mock_interface.rm = mock.Mock()
    # 3. Instantiate a real Operator
    self.operator = op.Operator(self.mock_interface)
    self.operator.run_id = 'test-run'
    self.operator.messages = MockMessage()
    # 4. Define standard parameters.
    self.params = {
        flags.PROJECT_ID:
            DUMMY_PROJECT_ID,
        'start_time':
            datetime.datetime(2025, 1, 1, tzinfo=datetime.timezone.utc),
        'end_time':
            datetime.datetime(2025, 1, 2, tzinfo=datetime.timezone.utc),
    }
    self.operator.parameters = self.params


class OrgPolicyCheckTest(GeneralizedStepsTestBase):
  """Test OrgPolicyCheck step."""

  def test_org_policy_enforced_and_expected_enforced(self):
    step = generalized_steps.OrgPolicyCheck(
        constraint='constraints/compute.disableSerialPortAccess',
        is_enforced=True,
    )
    with op.operator_context(self.operator):
      self.operator.set_step(step)
      step.execute()
    self.mock_interface.add_ok.assert_called_once()
    self.mock_interface.add_failed.assert_not_called()

  def test_org_policy_not_enforced_and_expected_enforced(self):
    step = generalized_steps.OrgPolicyCheck(
        constraint='constraints/iam.disableCrossProjectServiceAccountUsage',
        is_enforced=True,
    )
    with op.operator_context(self.operator):
      self.operator.set_step(step)
      step.execute()
    self.mock_interface.add_ok.assert_not_called()
    self.mock_interface.add_failed.assert_called_once()

  def test_org_policy_not_enforced_and_expected_not_enforced(self):
    step = generalized_steps.OrgPolicyCheck(
        constraint='constraints/iam.disableCrossProjectServiceAccountUsage',
        is_enforced=False,
    )
    with op.operator_context(self.operator):
      self.operator.set_step(step)
      step.execute()
    self.mock_interface.add_ok.assert_called_once()
    self.mock_interface.add_failed.assert_not_called()

  def test_org_policy_enforced_and_expected_not_enforced(self):
    step = generalized_steps.OrgPolicyCheck(
        constraint='constraints/compute.disableSerialPortAccess',
        is_enforced=False,
    )
    with op.operator_context(self.operator):
      self.operator.set_step(step)
      step.execute()
    self.mock_interface.add_ok.assert_not_called()
    self.mock_interface.add_failed.assert_called_once()

  def test_org_policy_enforced_with_project_parameter(self):
    step = generalized_steps.OrgPolicyCheck(
        constraint='constraints/compute.disableSerialPortAccess',
        is_enforced=True,
        project=DUMMY_PROJECT_ID,
    )
    with op.operator_context(self.operator):
      self.operator.set_step(step)
      step.execute()
    self.mock_interface.add_ok.assert_called_once()
    self.mock_interface.add_failed.assert_not_called()


if __name__ == '__main__':
  unittest.main()
