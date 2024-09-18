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
from typing import Any, Optional, Tuple

from gcpdiag import models
from gcpdiag.runbook.constants import *  # pylint: disable=unused-wildcard-import, wildcard-import
from gcpdiag.runbook.report import InteractionInterface

context: models.Context
operator: 'Operator'


class Operator(dict):
  """ Operation Object used to manipulate context, message and parameter data"""
  messages: models.Messages
  context: models.Context
  parameter: models.Parameter
  interface: InteractionInterface
  run_id: str
  _step = None
  _tree = None

  def __init__(self, interface: InteractionInterface):
    self.interface = interface

  def set_run_id(self, run_id):
    self.run_id = run_id

  def set_parameters(self, p):
    self.parameters = p

  def create_context(self, p, project_id=None):
    self.context = models.Context(project_id=project_id, parameters=p)

  def set_messages(self, m):
    self.messages = m

  def set_step(self, s):
    self._step = s

  def set_tree(self, t):
    self._tree = t

  @property
  def step(self):
    return self._step

  @property
  def tree(self):
    return self._tree


@contextmanager
def operator_context(new_operator):
  """Temporarily sets the global context and operator in op.py module"""
  global context, operator
  # Set up the new context and operator for a step
  context, operator = new_operator.context, new_operator
  try:
    yield
  finally:
    operator = None
    context = None


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
  return operator.parameters.get(key, default)


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
  operator.parameters[key] = value


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


def info(message: str, step_type='INFO') -> None:
  """Send an informational message to the user"""
  operator.interface.info(message, step_type)
  operator.interface.rm.add_step_info_metadata(
      run_id=operator.run_id,
      step_execution_id=operator.step.execution_id,
      value=message)


def prep_rca(resource: Optional[models.Resource], template, suffix,
             kwarg) -> None:
  """Parses a log form and complex Jinja templates for root cause analysis (RCA)."""
  return operator.interface.prepare_rca(run_id=operator.run_id,
                                        resource=resource,
                                        template=template,
                                        suffix=suffix,
                                        step=operator.step,
                                        context=kwarg)


def add_skipped(resource: Optional[models.Resource], reason: str) -> None:
  """Sends a skip message for a step to the user and store it in the report"""
  operator.interface.add_skipped(run_id=operator.run_id,
                                 resource=resource,
                                 reason=reason,
                                 step_execution_id=operator.step.execution_id)


def add_ok(resource: models.Resource, reason: str = '') -> None:
  """Sends a success message for a step to the user and store it in the report"""
  operator.interface.add_ok(run_id=operator.run_id,
                            resource=resource,
                            reason=reason,
                            step_execution_id=operator.step.execution_id)


def add_failed(resource: models.Resource, reason: str, remediation: str) -> Any:
  """Sends a failure message for a step to the user and store it in the report"""
  return operator.interface.add_failed(
      run_id=operator.run_id,
      resource=resource,
      reason=reason,
      remediation=remediation,
      step_execution_id=operator.step.execution_id)


def add_uncertain(resource: models.Resource,
                  reason: str,
                  remediation: str = None,
                  human_task_msg: str = '') -> Any:
  """Sends an inconclusive message for a step to the user and store it in the report"""
  return operator.interface.add_uncertain(
      run_id=operator.run_id,
      resource=resource,
      reason=reason,
      remediation=remediation,
      step_execution_id=operator.step.execution_id,
      human_task_msg=human_task_msg)


def get_step_outcome(execution_id) -> Tuple[Any, dict]:
  """Returns the overall evaluation result of a step

  You can only check for steps that have already been executed.
  It is not possible to get the status of the current step, it's descendants or steps
  in branches not yet executed.

  Returns:
    a dict of totals by status representing outcome of resource evaluations
    or empty dict if the step hasn't been executed.
  """
  step_result = operator.interface.rm.reports[operator.run_id].results.get(
      execution_id)
  if not step_result:
    return (None, {})
  return (step_result.overall_status, step_result.totals_by_status)


def step_ok(execution_id) -> bool:
  """Checks if the step with the provided run id passed evaluation"""
  overall_status, _ = get_step_outcome(execution_id)
  return overall_status == 'ok'


def step_failed(execution_id) -> bool:
  """Checks if the step with the provided run id failed evaluation"""
  overall_status, _ = get_step_outcome(execution_id)
  return overall_status == 'failed'


def step_uncertain(execution_id) -> bool:
  """Checks if the step with the provided run id has an indeterminate evaluation"""
  overall_status, _ = get_step_outcome(execution_id)
  return overall_status == 'uncertain'


def step_skipped(execution_id) -> bool:
  """Checks if the step with the provided run id was skipped"""
  overall_status, _ = get_step_outcome(execution_id)
  return overall_status == 'skipped'


def step_unexecuted(execution_id) -> bool:
  """Checks if the step with the provided run id was never executed"""
  overall_status, _ = get_step_outcome(execution_id)
  return overall_status is None


def add_metadata(key, value):
  operator.interface.rm.add_step_metadata(
      run_id=operator.run_id,
      step_execution_id=operator.step.execution_id,
      key=key,
      value=value)


def get_metadata(key, step_execution_id=None):
  step_execution_id = step_execution_id or operator.step.execution_id
  return operator.interface.rm.get_step_metadata(
      run_id=operator.run_id, step_execution_id=step_execution_id, key=key)


def get_all_metadata(step_execution_id=None):
  step_execution_id = step_execution_id or operator.step.execution_id
  return operator.interface.rm.get_all_step_metadata(
      run_id=operator.run_id, step_execution_id=step_execution_id)
