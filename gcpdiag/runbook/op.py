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
  """
  Parses the Jinja template block linked the calling step

  This function takes a scenario key and template variables as input, and uses them
  to parse a Jinja template. The template is linked to a specific step, and the
  function returns the parsed message.

  Usage:
      op.prep_msg(op.SUCCESS_REASON, template_var1=value1, template_var2=value2)

  Args:
      key (str): The scenario key that determines which template to use.
      **kwargs: Arbitrary keyword arguments representing the variables to be passed into the
                Jinja template.

  Returns:
      str: The parsed message from the linked Jinja template.

"""
  return operator.messages.get_msg(key, **kwargs)


def get(key, default=None):
  """
  Retrieve user provided runbook parameter values

  It retrieves the user-provided parameter value for the given key or returns
  the default value if the key is not found. The default value can be what is defined at the
  diagnostic tree parameter declaration or the default value provided to this method. If both
  method and diagnostic tree level parameters are provided, the tree level overrides the method
  default.

    Args:
      key (str): The key for the parameter to be retrieved.
      default (any, optional): The default value to return if no value. Defaults to None.

    Returns:
      any: The value associated with the key if it exists, otherwise the default value.

    Usage:
      value = op.get('parameter_name')
    """
  return operator.context.parameters.get(key, default)


def put(key, value):
  """
    Create a new parameter or update an existing parameter

    This function assigns the given value to the specified key within the runbook's
    context parameters.

    Args:
        key (str): The key for the parameter to be set.
        value (any): The value to be associated with the key.

    Usage:
        operator.put('parameter_name', 'value')
  """
  operator.context.parameters[key] = value


def prompt(message: str,
           kind: str = '',
           options: dict = None,
           choice_msg: str = '') -> Any:
  """
    Displays a prompt to the user with the given message and choice message.

    This function interfaces with the operator's prompt mechanism to display a message to the user.
    It can include additional information such as the the kind of prompt,
    available options, and a message for choosing from options.

    Args:
      message (str): The main message to display to the user.
      kind (str, optional): The type of prompt, CONFIRMATION, HUMAN_TASK
      options (dict, optional): A dictionary of options that the user can choose from.
      choice_msg (str, optional): An optional message guiding the user to make a choice from the
      options. Defaults to an empty string.

    Returns:
      Any: User response

    Usage:
      op.prompt(message='Should we check the remaining interfaces as well?',
                kind=op.CONFIRMATION,
                choice_msg='Select one of the options below:',
                options={'y': 'Yes, all remaining interfaces', 'n': 'No Proceed'}
            )
    """
  return operator.interface.prompt(message=message,
                                   kind=kind,
                                   options=options,
                                   choice_msg=choice_msg)


def info(message: str,
         resource=None,
         store_in_report=False,
         step_type='INFO') -> None:
  """Send an infomrmal message to the user"""
  operator.interface.info(message, resource, store_in_report, step_type)


def prep_rca(resource: Optional[models.Resource], template, suffix,
             kwarg) -> None:
  """Parses a log form and complex Jinja templates for root cause analysis (RCA)."""
  return operator.interface.prepare_rca(resource, template, suffix, kwarg)


def add_skipped(resource: Optional[models.Resource], reason: str) -> None:
  """Sends a skip message for a step to the user and store it in the report"""
  operator.interface.add_skipped(resource=resource, reason=reason)


def add_ok(resource: models.Resource, reason: str = '') -> None:
  """Sends a success message for a step to the user and store it in the report"""
  operator.interface.add_ok(resource=resource, reason=reason)


def add_failed(resource: models.Resource, reason: str, remediation: str) -> Any:
  """Sends a failure message for a step to the user and store it in the report"""
  return operator.interface.add_failed(resource, reason, remediation)


def add_uncertain(resource: models.Resource,
                  reason: str,
                  remediation: str = None,
                  human_task_msg: str = '') -> Any:
  """Sends an inconclusive message for a step to the user and store it in the report"""
  return operator.interface.add_uncertain(resource, reason, remediation,
                                          human_task_msg)
