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
"""Operator Module"""

from contextlib import contextmanager
from typing import Any, Optional

from gcpdiag import models
from gcpdiag.runbook.constants import *  # pylint: disable=unused-wildcard-import, wildcard-import
from gcpdiag.runbook.report import InteractionInterface

context: models.Context
operator: 'Operator'


class Operator(dict):
  """ Operation Object used to manipulate context, message and parameter data"""
  messages: models.Messages
  context: models.Context
  interface: InteractionInterface

  def __init__(self, c: models.Context, i: InteractionInterface):
    self.context = c
    self.interface = i

  def set_context(self, c):
    self.context = c

  def set_parameters(self, p):
    self.context.parameters = p

  def set_messages(self, m):
    self.messages = m


@contextmanager
def operator_context(new_operator):
  """Temporarily sets the global context and operator in op.py module"""
  global context, operator
  # Set up the new context and operator for a step
  context, operator = new_operator.context, new_operator
  try:
    yield
  finally:
    context = None
    operator = None


# pylint: disable=protected-access
def prep_msg(key, **kwargs):
  return operator.messages.get_msg(key, **kwargs)


def get(key, default=None):
  return operator.context.parameters.get(key, default)


def put(key, value):
  operator.context.parameters[key] = value


def prompt(message: str,
           step: str = '',
           options: dict = None,
           choice_msg: str = '') -> None:
  return operator.interface.prompt(message=message,
                                   step=step,
                                   options=options,
                                   choice_msg=choice_msg)


def info(message: str,
         resource=None,
         store_in_report=False,
         step_type='INFO') -> None:
  operator.interface.info(message, resource, store_in_report, step_type)


def prep_rca(resource: Optional[models.Resource], template, suffix,
             kwarg) -> None:
  return operator.interface.prepare_rca(resource, template, suffix, kwarg)


def add_skipped(resource: Optional[models.Resource], reason: str) -> None:
  operator.interface.add_skipped(resource=resource, reason=reason)


def add_ok(resource: models.Resource, reason: str = '') -> None:
  operator.interface.add_ok(resource=resource, reason=reason)


def add_failed(resource: models.Resource, reason: str, remediation: str) -> Any:
  return operator.interface.add_failed(resource, reason, remediation)


def add_uncertain(resource: models.Resource,
                  reason: str,
                  remediation: str = None,
                  human_task_msg: str = '') -> Any:
  return operator.interface.add_uncertain(resource, reason, remediation,
                                          human_task_msg)
