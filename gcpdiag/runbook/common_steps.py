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

from gcpdiag import config, models, runbook
from gcpdiag.models import Resource
from gcpdiag.runbook import constants
from gcpdiag.runbook.parameters import AUTO


class HumanTask(runbook.Step):
  """Manual Step where a human simply accesses and confirms an issue."""
  resource: Resource

  def __init__(
      self,
      resource=lambda: None,
      step_type=constants.StepType.MANUAL,
      context=None,
      interface=None,
      parameters: models.Parameter = None,
  ):
    super().__init__(context=context,
                     interface=interface,
                     parameters=parameters,
                     step_type=step_type)
    self.resource = resource

  def execute(self):
    """Human Task"""
    if config.get(AUTO):
      self.interface.add_skipped(None,
                                 reason=self.prompts[constants.SKIPPED_REASON])
      return

    response = self.guide()
    if response == self.interface.output.UNCERTAIN:
      response = self.interface.add_uncertain(
          self.resource,
          reason=self.prompts[constants.UNCERTAIN_REASON],
          remediation=self.prompts[constants.UNCERTAIN_REMEDIATION])
    elif response == self.interface.output.YES:
      self.interface.add_ok(self.resource,
                            self.prompts[constants.SUCCESS_REASON])
    elif response == self.interface.output.NO:
      self.interface.add_failed(
          self.resource,
          reason=self.prompts[constants.FAILURE_REASON],
          remediation=self.prompts[constants.FAILURE_REMEDIATION])

  def guide(self):
    if callable(self.resource):
      self.resource = self.resource()
    response = self.interface.prompt(
        step=self.interface.output.CONFIRMATION,
        message=self.prompts[constants.INSTRUCTIONS_MESSAGE],
        options=constants.INSTRUCTIONS_CHOICE_OPTIONS)
    return response

  def set_prompts(self):
    self.prompts = {
        constants.SKIPPED_REASON:
            'Human Tasks was skipped as runbook is running autonomous mode'
    }
