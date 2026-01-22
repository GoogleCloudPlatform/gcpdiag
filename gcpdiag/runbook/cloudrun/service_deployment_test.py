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
"""Test class for cloudrun/Service_deployment"""

import datetime
import unittest
from unittest import mock

from gcpdiag import config
from gcpdiag.queries import apis_stub
from gcpdiag.runbook import cloudrun as cloudrun_rb
from gcpdiag.runbook import op, snapshot_test_base
from gcpdiag.runbook.cloudrun import flags, service_deployment


class TestInvalidContainer(snapshot_test_base.RulesSnapshotTestBase):
  rule_pkg = cloudrun_rb
  runbook_name = 'cloudrun/service-deployment'
  config.init({'auto': True, 'interface': 'cli'})

  rule_parameters = [
      {
          'project_id': 'gcpdiag-cloudrun2-aaaa',
          'cloudrun_service_name': 'invalid-container',
          'region': 'us-central1',
      },
      {
          'project_id': 'gcpdiag-cloudrun2-aaaa',
          'cloudrun_service_name': 'image-does-not-exist',
          'region': 'us-central1',
      },
      {
          'project_id': 'gcpdiag-cloudrun2-aaaa',
          'cloudrun_service_name': 'no-image-permission',
          'region': 'us-central1',
      },
  ]


class MockMessage:
  """Mock messages for testing."""

  def get_msg(self, key, **kwargs):
    del kwargs
    return f'{key}'


class ServiceDeploymentTest(unittest.TestCase):

  def test_legacy_parameter_handler(self):
    params = {flags.SERVICE_NAME: 'test-service'}
    sd = service_deployment.ServiceDeployment()
    sd.legacy_parameter_handler(params)
    self.assertEqual(params[flags.CLOUDRUN_SERVICE_NAME], 'test-service')

  def test_build_tree(self):
    sd = service_deployment.ServiceDeployment()
    sd.build_tree()
    self.assertIsInstance(sd.start, service_deployment.ServiceDeploymentStart)
    self.assertEqual(len(sd.start.steps), 1)
    self.assertIsInstance(sd.start.steps[0],
                          service_deployment.ServiceDeploymentCodeStep)


class StepTestBase(unittest.TestCase):
  """Base class for step tests."""

  def setUp(self):
    super().setUp()
    self.enterContext(
        mock.patch('gcpdiag.queries.apis.get_api', new=apis_stub.get_api_stub))

    self.params = {
        flags.PROJECT_ID: 'gcpdiag-cloudrun2-aaaa',
        flags.REGION: 'us-central1',
        flags.CLOUDRUN_SERVICE_NAME: 'invalid-container',
        'start_time': datetime.datetime.now(),
        'end_time': datetime.datetime.now(),
    }

    self.mock_interface = mock.create_autospec(op.InteractionInterface,
                                               instance=True)
    self.mock_interface.rm = mock.Mock()
    self.operator = op.Operator(self.mock_interface)
    self.operator.run_id = 'test-run'
    self.operator.parameters = self.params
    self.operator.messages = MockMessage()


class ServiceDeploymentStartTest(StepTestBase):

  def test_execute_success(self):
    self.params[flags.CLOUDRUN_SERVICE_NAME] = 'invalid-container'
    step = service_deployment.ServiceDeploymentStart()
    with op.operator_context(self.operator):
      self.operator.set_step(step)
      step.execute()
    self.mock_interface.add_skipped.assert_not_called()

  def test_execute_service_not_found(self):
    self.params[flags.CLOUDRUN_SERVICE_NAME] = 'service-does-not-exist'
    step = service_deployment.ServiceDeploymentStart()
    with op.operator_context(self.operator):
      self.operator.set_step(step)
      step.execute()
    self.mock_interface.add_skipped.assert_called_once()


class ServiceDeploymentCodeStepTest(StepTestBase):

  def test_execute(self):
    step = service_deployment.ServiceDeploymentCodeStep()
    with op.operator_context(self.operator):
      self.operator.set_step(step)
      step.execute()
    self.assertEqual(len(step.steps), 3)
    self.assertIsInstance(step.steps[0],
                          service_deployment.ContainerFailedToStartStep)
    self.assertIsInstance(step.steps[1],
                          service_deployment.ImageWasNotFoundStep)
    self.assertIsInstance(step.steps[2],
                          service_deployment.NoPermissionForImageStep)


class ContainerFailedToStartStepTest(StepTestBase):

  def test_container_failed_to_start(self):
    self.params[flags.CLOUDRUN_SERVICE_NAME] = 'invalid-container'
    step = service_deployment.ContainerFailedToStartStep()
    with op.operator_context(self.operator):
      self.operator.set_step(step)
      step.execute()
    self.mock_interface.add_failed.assert_called_once()

  def test_container_started(self):
    self.params[flags.CLOUDRUN_SERVICE_NAME] = 'image-does-not-exist'
    step = service_deployment.ContainerFailedToStartStep()
    with op.operator_context(self.operator):
      self.operator.set_step(step)
      step.execute()
    self.mock_interface.add_failed.assert_not_called()


class ImageWasNotFoundStepTest(StepTestBase):

  def test_image_not_found(self):
    self.params[flags.CLOUDRUN_SERVICE_NAME] = 'image-does-not-exist'
    step = service_deployment.ImageWasNotFoundStep()
    with op.operator_context(self.operator):
      self.operator.set_step(step)
      step.execute()
    self.mock_interface.add_failed.assert_called_once()

  def test_image_found(self):
    self.params[flags.CLOUDRUN_SERVICE_NAME] = 'invalid-container'
    step = service_deployment.ImageWasNotFoundStep()
    with op.operator_context(self.operator):
      self.operator.set_step(step)
      step.execute()
    self.mock_interface.add_failed.assert_not_called()


class NoPermissionForImageStepTest(StepTestBase):

  def test_no_permission(self):
    self.params[flags.CLOUDRUN_SERVICE_NAME] = 'no-image-permission'
    step = service_deployment.NoPermissionForImageStep()
    with op.operator_context(self.operator):
      self.operator.set_step(step)
      step.execute()
    self.mock_interface.add_failed.assert_called_once()

  def test_has_permission(self):
    self.params[flags.CLOUDRUN_SERVICE_NAME] = 'invalid-container'
    step = service_deployment.NoPermissionForImageStep()
    with op.operator_context(self.operator):
      self.operator.set_step(step)
      step.execute()
    self.mock_interface.add_failed.assert_not_called()
