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
"""Reusable Steps application to any product"""

import typing

import googleapiclient.http
from boltons.iterutils import get_path

from gcpdiag import config, models, runbook
from gcpdiag.models import Resource
from gcpdiag.queries import apis
from gcpdiag.runbook import flags
from gcpdiag.runbook.gcp import constants
from gcpdiag.runbook.gcp.flags import INTERACTIVE_MODE


class HumanTask(runbook.Step):
  """Manual Step where a human simply accesses and confirms an issue."""
  resource: Resource

  def __init__(self,
               resource=lambda: None,
               step_type=constants.StepType.MANUAL):
    super().__init__(step_type=step_type)
    self.resource = resource

  def execute(self):
    """Human Task"""
    if config.get(INTERACTIVE_MODE):
      self.op.add_skipped(None, reason=self.prompts[constants.SKIPPED_REASON])
      return

    response = self.guide()
    if response == self.op.output.UNCERTAIN:
      response = self.op.add_uncertain(
          self.resource,
          reason=self.prompts[constants.UNCERTAIN_REASON],
          remediation=self.prompts[constants.UNCERTAIN_REMEDIATION])
    elif response == self.op.output.YES:
      self.op.add_ok(self.resource, self.prompts[constants.SUCCESS_REASON])
    elif response == self.op.output.NO:
      self.op.add_failed(
          self.resource,
          reason=self.prompts[constants.FAILURE_REASON],
          remediation=self.prompts[constants.FAILURE_REMEDIATION])

  def guide(self):
    if callable(self.resource):
      self.resource = self.resource()
    response = self.op.prompt(
        step=self.op.output.CONFIRMATION,
        message=self.prompts[constants.INSTRUCTIONS_MESSAGE],
        options=constants.INSTRUCTIONS_CHOICE_OPTIONS)
    return response

  def set_prompts(self):
    self.prompts = {
        constants.SKIPPED_REASON:
            'Human Tasks was skipped as runbook is running autonomous mode'
    }


class ResourceAttributeCheck(runbook.Step):
  """Check of a gcp resource has the expected attribute for a resource.

  TODO: explain what this does.
  """
  resource_query: typing.Callable
  query_kwargs: dict
  evaluator = None
  attribute: tuple
  expected_value: str
  expected_value_type: type = str
  extract_args: dict = {}
  message_args: dict = {}

  resource: Resource

  def execute(self):
    """Verifying resource has expected value..."""
    try:
      self.resource = self.resource_query(**self.query_kwargs)
      # TODO: change this.
    except googleapiclient.errors.HttpError:
      self.op.add_uncertain(self.resource,
                            reason=self.op.get_msg(constants.UNCERTAIN_REASON),
                            remediation=self.op.get_msg(
                                constants.UNCERTAIN_REMEDIATION))

    if self.extract_args is not None:
      for k, v in self.extract_args.items():
        if v['source'] == Resource:
          # pylint:disable=protected-access
          self.message_args[k] = get_path(self.resource._resource_data,
                                          v['attribute'],
                                          default=v.get('default'))
        if v['source'] == models.Parameter:
          self.message_args[k] = self.op.get(v['attribute'])

    if self.evaluator is not None:
      res = self.evaluator(self.resource)
      if res[constants.SUCCESS_REASON]:
        self.op.add_ok(self.resource, self.op.get_msg(constants.SUCCESS_REASON))
      elif res[constants.FAILURE_REASON]:
        self.op.add_failed(self.resource,
                           reason=self.op.get_msg(constants.FAILURE_REASON),
                           remediation=self.op.get_msg(
                               constants.FAILURE_REMEDIATION))
    if self.attribute:
      # pylint:disable=protected-access
      actual_value = get_path(self.resource._resource_data,
                              self.attribute,
                              default=None)
      actual_value = self.expected_value_type(actual_value)
      if self.expected_value == actual_value:
        self.op.add_ok(
            self.resource,
            self.op.get_msg(constants.SUCCESS_REASON, **self.message_args))
      else:
        self.op.add_failed(self.resource,
                           reason=self.op.get_msg(constants.FAILURE_REASON,
                                                  **self.message_args),
                           remediation=self.op.get_msg(
                               constants.FAILURE_REMEDIATION,
                               **self.message_args))


class ServiceApiStatusCheck(runbook.Step):
  """Check whether or not a service has been enabled for use by a consumer

  Checks is a Cloud API service is enabled or not. Guides the user to enable
  the service if it's expected to be enabled and vice versa.

  Attributes:
      api_name (str): The name of the service to check.
      expected_state (str): The expected state of the service, used to verify
                            against the actual service state retrieved during
                            execution. API state has to be one of the value of
                            gcp.constants.APIState

  """
  api_name: str
  expected_state: str
  template: str = 'api::default'

  def execute(self):
    """Verifying Cloud API state of {api_name}..."""
    services = apis.list_services_with_state(self.op[flags.PROJECT_ID])
    service_name = f'{self.api_name}.{config.get("universe_domain")}'
    actual_state = services.get(service_name)
    if self.expected_state == actual_state:
      self.op.add_ok(
          self.resource,
          self.op.get_msg(constants.SUCCESS_REASON,
                          service_name=service_name,
                          expected_state=self.expected_state))
    else:
      if self.expected_state == constants.APIState.ENABLED:
        remediation = self.op.get_msg(constants.FAILURE_REMEDIATION,
                                      service_name=service_name,
                                      project_id=self.op[flags.PROJECT_ID])
      if self.expected_state == constants.APIState.DISABLED:
        remediation = self.op.get_msg(constants.FAILURE_REMEDIATION_ALT1,
                                      service_name=service_name,
                                      project_id=self.op[flags.PROJECT_ID])
      self.op.add_failed(self.resource,
                         reason=self.op.get_msg(constants.FAILURE_REASON),
                         remediation=remediation)
