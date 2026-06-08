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
"""Test class for dataflow.generalized_steps."""

import datetime
import unittest
from unittest import mock

from gcpdiag.queries import apis_stub, dataflow
from gcpdiag.runbook import op
from gcpdiag.runbook.dataflow import flags, generalized_steps

DUMMY_PROJECT_ID = 'gcpdiag-dataflow1-aaaa'
DUMMY_JOB_ID = '2024-06-19_09_43_07-14927685200167458422'
DUMMY_REGION = 'us-central1'


class MockMessage:
  """Mock messages for testing."""

  def get_msg(self, key, **kwargs):
    del kwargs
    return f'{key}'


class GeneralizedStepsTestBase(unittest.TestCase):
  """Base class for Dataflow generalized step tests."""

  def setUp(self):
    super().setUp()
    # 1. Patch get_api with the stub.
    self.enterContext(mock.patch('gcpdiag.queries.apis.get_api', new=apis_stub.get_api_stub))
    # 2. Create a mock interface to capture outputs
    self.mock_interface = mock.create_autospec(op.InteractionInterface, instance=True)
    self.mock_interface.rm = mock.Mock()
    # 3. Instantiate a real Operator
    self.operator = op.Operator(self.mock_interface)
    self.operator.run_id = 'test-run'
    self.operator.messages = MockMessage()
    # 4. Define standard parameters.
    self.params = {
      flags.PROJECT_ID: DUMMY_PROJECT_ID,
      flags.DATAFLOW_JOB_ID: DUMMY_JOB_ID,
      flags.JOB_REGION: DUMMY_REGION,
      'start_time': datetime.datetime(2025, 1, 1, tzinfo=datetime.timezone.utc),
      'end_time': datetime.datetime(2025, 1, 2, tzinfo=datetime.timezone.utc),
    }
    self.operator.parameters = self.params


# Refactor the common unittests from failedstreamingpipeline to this generalized test class
# to allow parallel development of the streaming pipeline runbook.


class ValidSdkTest(GeneralizedStepsTestBase):
  """Test ValidSdk step."""

  def test_valid_sdk(self):
    step = generalized_steps.ValidSdk()
    with op.operator_context(self.operator):
      self.operator.set_step(step)
      step.execute()
    self.mock_interface.add_ok.assert_called_once()
    self.mock_interface.add_failed.assert_not_called()

  @mock.patch('gcpdiag.queries.dataflow.get_job')
  def test_invalid_sdk(self, mock_get_job):
    mock_job = mock.Mock(spec=dataflow.Job)
    mock_job.sdk_support_status = 'DEPRECATED'
    mock_get_job.return_value = mock_job
    step = generalized_steps.ValidSdk()
    with op.operator_context(self.operator):
      self.operator.set_step(step)
      step.execute()
    self.mock_interface.add_ok.assert_not_called()
    self.mock_interface.add_failed.assert_called_once()


if __name__ == '__main__':
  unittest.main()
