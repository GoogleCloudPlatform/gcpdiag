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
"""Operation Object"""

from typing import Any, Optional

from gcpdiag import models
from gcpdiag.runbook.report import InteractionInterface


class Operation(dict):
  """ Operation Object used to manipulate context, message and parameter data"""
  messages: models.Messages
  context: models.Context
  interface: InteractionInterface

  def __init__(self, context: models.Context, interface):
    self.context = context
    self.interface = interface

  def set_context(self, context):
    self.context = context

  def set_parameters(self, parameters):
    self.context.parameters = parameters

  def set_messages(self, messages):
    self.messages = messages

  def get_msg(self, key, **kwargs):
    return self.messages.get_msg(key, **kwargs)

  def get(self, key, default=None):
    return self.context.parameters.get(key, default)

  def __getitem__(self, key):
    # Redirect item access to parameters
    return self.context.parameters[key]

  def __setitem__(self, key, value):
    # Redirect item setting to parameters
    self.context.parameters[key] = value

  def prompt(self,
             message: str,
             step: str = '',
             options: dict = None,
             choice_msg: str = '') -> None:
    return self.interface.prompt(message=message,
                                 step=step,
                                 options=options,
                                 choice_msg=choice_msg)

  def info(self,
           message: str,
           resource=None,
           store_in_report=False,
           step_type='INFO') -> None:
    self.interface.info(step_type=step_type,
                        message=message,
                        resource=resource,
                        store_in_report=store_in_report)

  def prepare_rca(self, resource: Optional[models.Resource], template, suffix,
                  context) -> None:
    self.interface.prepare_rca(resource=resource,
                               template=template,
                               suffix=suffix,
                               context=context)

  def add_skipped(self, resource: Optional[models.Resource],
                  reason: str) -> None:
    self.interface.add_skipped(resource=resource, reason=reason)

  def add_ok(self, resource: models.Resource, reason: str = '') -> None:
    self.interface.add_ok(resource=resource, reason=reason)

  def add_failed(self, resource: models.Resource, reason: str,
                 remediation: str) -> Any:
    return self.interface.add_failed(resource=resource,
                                     reason=reason,
                                     remediation=remediation)

  def add_uncertain(self,
                    resource: models.Resource,
                    reason: str,
                    remediation: str = None,
                    human_task_msg: str = '') -> Any:
    return self.interface.add_uncertain(resource=resource,
                                        reason=reason,
                                        remediation=remediation,
                                        human_task_msg=human_task_msg)
