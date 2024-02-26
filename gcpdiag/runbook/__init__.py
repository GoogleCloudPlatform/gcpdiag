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
"""Runbook command: find potential issues in GCP projects."""

import logging
import sys
from abc import abstractmethod
from collections import OrderedDict, deque
from datetime import datetime, timezone
from typing import Any, Deque, Dict, List, Set, final

import googleapiclient.errors

from gcpdiag import config, models, utils
from gcpdiag.runbook import exceptions, report, util
from gcpdiag.runbook.constants import STEP_MESSAGE, StepType
from gcpdiag.runbook.parameters import AUTO

DiagnosticTreeRegister: Dict[str, 'DiagnosticTree'] = {}


class Step:
  """
  Represents a step in a diagnostic or runbook process.
  """
  steps: List['Step']
  interface: report.InteractionInterface

  def __init__(self,
               parent: 'Step' = None,
               context=None,
               interface=None,
               parameters: models.Parameter = None,
               step_type=StepType.AUTOMATED,
               name=None):
    """
    Initializes a new instance of the Step class.
    """
    self.name = name or util.generate_random_string()
    self._id = '.'.join([self.__module__, self.__class__.__name__, self.name])
    self.steps = []
    self.context = context
    self._parameters = parameters
    self.interface = interface
    self.type = step_type
    self.prompts: Dict = {}
    self.output = None
    if parent:
      parent.add_step(step=self)
    self.set_prompts()

  @property
  def run_id(self):
    return self._id

  @property
  def op(self) -> models.Parameter:
    return self._parameters or models.Parameter()

  @final
  def hook_execute(self, context: models.Context, interface):
    """
    Executes the step using the given context and interface.

    Parameters:
        context: The context in which the step is executed.
        interface: The interface used for interactions during execution.
    """
    self.context = context if context else self.context
    self._parameters = self._parameters or context._parameters  # pylint: disable=protected-access
    self.interface = interface if interface else self.interface
    self.execute()

  def execute(self):
    """Executes the step using the given context and interface."""
    pass

  def set_prompts(self, prompt: Dict = None):
    if prompt:
      self.prompts.update(prompt)

  def add_step(self, step):
    """Child steps"""
    self.steps.append(step)

  def find_step(self, step: 'Step'):
    """Find a step by ID"""
    if self == step:
      return self
    for child in self.steps:
      result = child.find_step(step)
      if result:
        return result
    return None

  def __hash__(self) -> int:
    return hash((self.run_id, self.type))


class StartStep(Step):
  """Start Event of a Diagnotic tree"""

  def __init__(self,
               context=None,
               interface=None,
               parameters: models.Parameter = None):
    super().__init__(context, interface, parameters, step_type=StepType.START)


class CompositeStep(Step):
  """Composite Events of a Diagnotic tree"""

  def __init__(self,
               context=None,
               interface=None,
               parameters: models.Parameter = None):
    super().__init__(context,
                     interface,
                     parameters,
                     step_type=StepType.COMPOSITE)


class EndStep(Step):
  """End Event of a Diagnostic Tree"""

  def __init__(self,
               context=None,
               interface=None,
               parameters: models.Parameter = None):
    super().__init__(context, interface, parameters, step_type=StepType.END)

  def execute(self):
    if not config.get(AUTO):
      response = self.interface.prompt(task=self.interface.CONFIRMATION,
                                       message='Is your issue resolved?')
      if response == self.interface.NO:
        self.interface.prompt(message=(
            'Contact Google Cloud Support for further investigation.\n'
            'https://cloud.google.com/support/docs/customer-care-procedures\n'
            'Recommended: Submit the generated report to Google cloud support '
            'when opening a ticket.'))


class Gateway(Step):
  """
  Represents a decision point in a workflow, determining which path to take based on a condition.
  """

  def __init__(
      self,
      paths: Dict[Any, Step],
      condition=lambda: True,
      step_type=StepType.GATEWAY,
      context=None,
      interface=None,
      parameters: models.Parameter = None,
  ):
    """
    Initializes a new instance of the Gateway step.
    """
    super().__init__(context=context,
                     interface=interface,
                     parameters=parameters,
                     step_type=StepType.GATEWAY)
    self.condition = condition
    self.paths = paths
    self.type = step_type


class RunbookRule(type):
  """Metaclass for automatically registering subclasses of DiagnosticTree
  in a registry for easy lookup and instantiation based on product/rule ID."""

  def __new__(mcs, name, bases, namespace):
    new_class = super().__new__(mcs, name, bases, namespace)
    if name != 'DiagnosticTree' and bases[0] == DiagnosticTree:
      rule_id = util.camel_to_kebab(name)
      product = namespace.get('__module__', '').split('.')[-2].lower()
      DiagnosticTreeRegister[f'{product}/{rule_id}'] = new_class
    return new_class


class DiagnosticTree(metaclass=RunbookRule):
  """Represents a diagnostic tree for troubleshooting."""
  product: str
  rule_id: str
  name: str
  start: StartStep
  end: EndStep
  req_params: dict
  steps: List[Step]

  def __init__(self, context: models.Context):
    self.id = f'{self.__module__}.{self.__class__.__name__}'
    self.context = context
    self.product = self.__module__.rsplit('.')[-2].lower()
    self.rule_id = self.__class__.__name__.lower()
    self.name = f'{self.product}/{self.rule_id}'
    self.steps: List = []
    self.req_params = {}

  def set_context(self, context: models.Context):
    """Sets the execution context for the diagnostic tree."""
    self.context = context

  def add_step(self, parent: Step, child: Step):
    """Adds a diagnostic step to the tree."""
    if self.start is None:
      raise ValueError('Start step is empty. Set start step with'
                       ' builder.add_start() or tree.add_start()')
    parent_step = self.start.find_step(parent)
    if parent_step:
      parent_step.add_step(child)
    else:
      raise ValueError(
          f'Parent step with {parent.run_id} not found. Add parent first')

  def add_start(self, step: StartStep):
    """Adds a diagnostic step to the tree."""
    if hasattr(self, 'start') and getattr(self, 'start'):
      raise ValueError('start already exist')
    self.start = step

  def find_step(self, step_id):
    return self.start.find_step(step_id)

  @abstractmethod
  def build_tree(self):
    """Constructs the diagnostic tree."""
    raise NotImplementedError

  def __hash__(self):
    return str(self.product + self.rule_id).__hash__()

  def __str__(self):
    return f'{self.product}/{self.rule_id}'

  @property
  def doc_url(self) -> str:
    """Returns the documentation URL for the diagnostic tree."""
    return f'https://gcpdiag.dev/runbook/{self.product}/{self.rule_id}'


class DiagnosticTreeBuilder:
  """Diagnostic Tree Builder"""

  @abstractmethod
  def build(self) -> DiagnosticTree:
    raise NotImplementedError


class PyDiagnosticTreeBuilder(DiagnosticTreeBuilder):
  """
  Builder for constructing a DiagnosticTree instance defined in python.

  Attributes:
      tree (DiagnosticTree): The diagnostic tree being built.
  """

  def __init__(self, tree: DiagnosticTree):
    self.tree = tree

  def add_start(self, step: StartStep):
    """Sets the start step of the diagnostic tree."""
    if step.type == StepType.START:
      self.tree.add_start(step=step)

  def add_step(self, child: Step, parent: Step):
    """Adds an intermidate step to the diagnostic tree."""
    self.tree.add_step(parent=parent, child=child)

  def add_end(self, step: EndStep):
    """Sets the end step of the diagnostic tree."""
    if step.type == StepType.END:
      self.tree.end = step

  def add_gateway(self, gateway: Gateway):
    """Adds a gateway (decision point) to the diagnostic tree."""
    self.tree.start.steps.append(gateway)

  def build(self) -> DiagnosticTree:
    """Finalizes the tree construction and returns the built tree."""
    if self.tree.start is None:
      raise exceptions.InvalidDiagnosticTree(
          'The tree must have both a start step.')
    return self.tree

  def parse_to_bpmn(self):
    """Parse a built python tree into a bpmn 2.0 file"""
    raise NotImplementedError

  def parse_to_graphviz(self):
    """Parse a built python tree into a bpmn 2.0 file"""
    raise NotImplementedError


class BpmnDiagnosticTreeBuilder(DiagnosticTreeBuilder):
  pass


class GraphvizDiagnosticTreeBuilder(DiagnosticTreeBuilder):
  pass


class DiagnosticEngine:
  """Loads and Executes diagnostic trees.

  This class is responsible for loading and executing diagnostic trees
  based on provided rule name. It manages the diagnostic process, from
  validating required parameters to traversing and executing diagnostic
  steps.

  Attributes:
    _dt: Optional[DiagnosticTree] The current diagnostic tree being executed.
  """

  def __init__(self, rm: report.ReportManager = None, interface=None) -> None:
    """Initializes the DiagnosticEngine with required managers."""
    self.rm = rm or report.TerminalReportManager()
    self.interface = interface or report.InteractionInterface()

  def load_rule(self, name: str) -> None:
    """Loads a diagnostic tree by name ex gce/ssh.

    Attempts to retrieve a diagnostic tree registered under the given name.
    Exits the program if the tree is not found.

    Tree are registered onload of the class definition see RunbookRule metaclass

    Args:
      name: The name of the diagnostic tree to load.
    """
    try:
      self.dt = DiagnosticTreeRegister.get(name)
      if not self.dt:
        raise exceptions.DiagnosticTreeNotFound
    except exceptions.DiagnosticTreeNotFound as e:
      logging.error(e)
      sys.exit(2)

  def _check_required_paramaters(self, tree: DiagnosticTree):
    missing_param = {
        key: value
        for key, value in tree.req_params.items()
        if key not in tree.context._parameters  # pylint: disable=protected-access
    }
    if missing_param:
      logging.error('Required parameter(s): `%s` not provided. Exiting program',
                    ', '.join(missing_param.keys()))
      sys.exit(2)

  def run_diagnostic_tree(self, context: models.Context) -> None:
    """Executes the loaded diagnostic tree within a given context.

    Validates required parameters, builds the tree, and executes its steps.
    Handles exceptions during execution and generates a report upon completion.

    Args:
      context: The execution context for the diagnostic tree.
    """
    if not self.dt or not callable(self.dt):
      logging.error('Could not instantiate Diagnostic Tree')
      sys.exit(2)

    dt = self.dt(context)

    self._check_required_paramaters(dt)
    self.rm.tree = dt
    self.interface.set_dt(dt)
    self.interface.rm = self.rm
    self.interface.output.display_runbook_description(dt)

    try:
      dt.build_tree()
      # Default to generic end step if no end step is defined.
      self.find_path_dfs(step=dt.start,
                         context=context,
                         interface=self.interface)
      if not dt.end:
        dt.end.add_step(EndStep())
      self.find_path_dfs(step=dt.end, context=context)
    except (utils.GcpApiError, googleapiclient.errors.HttpError, RuntimeError,
            ValueError, KeyError) as err:
      if isinstance(err, googleapiclient.errors.HttpError):
        err = utils.GcpApiError(err)
      logging.warning('%s: %s while processing runbook rule: %s',
                      type(err).__name__, err, dt)

  def find_path_dfs(self,
                    step: Step,
                    context: models.Context,
                    interface=None,
                    executed_steps: Set = None):
    """Depth-first search to traverse and execute steps in the diagnostic tree.

    Args:
      step: The current step to execute.
      context: The execution context.
      interface: The interface managing user interactions.
      executed_steps: A set of executed step IDs to avoid cycles.
    """
    if executed_steps is None:
      executed_steps = set()

    if not interface:
      interface = self.interface

    self.run_step(step=step, context=context, interface=interface)
    executed_steps.add(step)
    for child in step.steps:  # Iterate over the children of the current step
      if child not in executed_steps:
        self.find_path_dfs(step=child,
                           context=context,
                           interface=interface,
                           executed_steps=executed_steps)

    return executed_steps

  def run_step(self, step: Step, context: models.Context, interface):
    """Executes a single step, handling user decisions for step re-evaluation or termination.

    Args:
      step: The diagnostic step to execute.
      context: The execution context.
      interface: The interface for interaction.
    """
    if step.prompts.get(STEP_MESSAGE):
      step_message = step.prompts[STEP_MESSAGE]
    else:
      step_message = step.execute.__doc__
    interface.output.prompt(step=step.type.value, message=step_message)

    choice = self._run(step, context, interface)
    while True:
      if choice is interface.output.RETEST:
        interface.output.prompt(step=interface.output.RETEST,
                                message='Re-evaluating recent failed step')
        choice = self._run(step, context, interface)
      elif step.type == StepType.END:
        self.rm.generate_report()
        break
      elif choice is interface.output.ABORT:
        logging.info('Terminating Runbook\n')
        sys.exit(2)
      elif step.type == StepType.START and (
        self.rm.results.get(step.run_id) is not None and \
          self.rm.results[step.run_id].status == 'skipped'):
        logging.info('Start Step was skipped. Can\'t proceed ...\n')
        sys.exit(2)
      elif choice is interface.output.CONTINUE:
        break
      elif (choice is not interface.output.RETEST and
            choice is not interface.output.CONTINUE and
            choice is not interface.output.ABORT):
        return choice

  def _run(self, step: Step, context: models.Context, interface):
    start = datetime.now(timezone.utc).timestamp()
    step.hook_execute(context, interface)
    end = datetime.now(timezone.utc).timestamp()
    if self.rm.results.get(step.run_id):
      self.rm.results[step.run_id].start_time_utc = start
      self.rm.results[step.run_id].end_time_utc = end
      return self.rm.results[step.run_id].prompt_response
    return None
