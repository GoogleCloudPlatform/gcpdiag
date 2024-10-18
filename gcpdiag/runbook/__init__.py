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

import ast
import builtins
import inspect
import logging
import sys
import textwrap
from collections import OrderedDict
from datetime import datetime, timedelta, timezone
from typing import Deque, Dict, List, Mapping, Set, Tuple, final

import googleapiclient.errors
from jinja2 import TemplateNotFound

from gcpdiag import caching, config, models, utils
from gcpdiag.queries import crm
from gcpdiag.runbook import constants, exceptions, flags, op, report, util

RunbookRegistry: Dict[str, 'DiagnosticTree'] = {}
StepRegistry: Dict[str, 'Step'] = {}


class MetaStep(type):
  """Metaclass for Steps in runbook"""

  @property
  def id(cls):
    """Class Id of a step"""
    return '.'.join([cls.__module__, cls.__name__])

  def __new__(mcs, name, bases, namespace):
    """Register all steps into StepRegistry exluding base classes"""
    new_class = super().__new__(mcs, name, bases, namespace)
    if name not in ('Step', 'Gateway', 'LintWrapper', 'StartStep', 'EndStep',
                    'CompositeStep') and bases[0] == Step:
      StepRegistry[new_class.id] = new_class
    return new_class


class Step(metaclass=MetaStep):
  """
  Represents a step in a diagnostic or runbook process.
  """
  steps: List['Step']
  template: str
  parameters: dict = {}

  def __init__(self,
               parent: 'Step' = None,
               step_type=constants.StepType.AUTOMATED,
               uuid=None,
               **parameters):
    """
    Initializes a new instance of the Step class.
    """
    self.uuid = uuid or util.generate_uuid()
    self.steps = []
    self.type = step_type
    self.prompts: models.Messages = models.Messages()
    self.product = self.__module__.split('.')[-2]
    self.doc_file_name = util.pascal_case_to_kebab_case(self.__class__.__name__)
    # allow developers to set this

    if parent:
      parent.add_child(child=self)

    # set object attributes with parameters
    # This is used by Bundles and Generalized steps
    if parameters:
      for attribute, value in parameters.items():
        setattr(self, attribute, value)

    self.set_prompts()

  @property
  def id(self):
    """Class Id of a step"""
    return self.__class__.id

  @property
  def execution_id(self):
    return '.'.join([self.id, self.uuid])

  def __str__(self):
    return self.execution_id

  @final
  def execute_hook(self, operator: op.Operator):
    """
    Executes the step using the given context and interface.

    Parameters:
        context: The context in which the step is executed.
        interface: The interface used for interactions during execution.
    """
    self.load_prompts()
    operator.set_messages(m=self.prompts)
    operator.interface.info(step_type=self.type.value,
                            message=self.execution_message)
    self.execute()

  def execute(self):
    """Executes the main diagnostic log for this step."""
    pass

  def set_prompts(self, prompt: models.Messages = None):
    # override existing messages
    if prompt:
      self.prompts.update(prompt)

  def load_prompts(self):
    if hasattr(self, 'template'):
      name = getattr(self, 'template').split('::')
    else:
      return

    if len(name) == 2:
      file_name, block_name = name[0], name[1]
      self.prompts.update(
          util.load_template_block(module_name=self.__module__,
                                   block_name=block_name,
                                   file_name=file_name))
    if len(name) == 3:
      file_name, block_name = name[1], name[2]
      self.prompts.update(
          util.load_template_block(module_name=name[0],
                                   block_name=block_name,
                                   file_name=file_name))

  def add_child(self, child):
    """Child steps"""
    self.steps.append(child)

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
    return hash((self.execution_id, self.type))

  @property
  def label(self):
    label = self.prompts.get_msg(constants.STEP_LABEL)
    if 'NOTICE' in label:
      label = util.pascal_case_to_title(self.__class__.__name__)
    return label

  @property
  def execution_message(self):
    attributes = vars(self)
    if self.prompts.get(constants.STEP_MESSAGE):
      formatted_message = self.prompts[constants.STEP_MESSAGE].format(
          attributes)
      formatted_message = formatted_message.rstrip('\n')
      return formatted_message.format(attributes)
    else:
      if self.execute.__doc__:
        return self.execute.__doc__.format(attributes)
      raise exceptions.InvalidStepOperation(
          f'Step {self} does not have an introductory message. '
          'Make sure execute() method has a docstring on the first line.')

  @property
  def long_desc(self):
    long_desc = None
    doc_lines = self.__doc__.splitlines()
    if len(doc_lines) >= 3:
      if doc_lines[1]:
        raise ValueError(
            f'Step {self.__class__.__name__} has a non-empty second line '
            'in the class docstring. Ensure the step\'s class docstring '
            'contains a one-line summary followed by an empty second line.')
      long_desc = '\n'.join(doc_lines[2:])
    return long_desc

  @property
  def short_desc(self):
    return self.__doc__.splitlines()[0]

  @property
  def doc_url(self):
    """Returns the documentation URL for the step."""
    return f'https://gcpdiag.dev/runbook/steps/{self.product}/{self.doc_file_name}'


class StartStep(Step):
  """Start Event of a Diagnostic tree"""

  def __init__(self):
    super().__init__(step_type=constants.StepType.START)

  def execute(self):
    """Executing default start step for runbooks..."""
    pass


class CompositeStep(Step):
  """Composite Events of a Diagnostic tree"""

  def __init__(self):
    super().__init__(step_type=constants.StepType.COMPOSITE)


class EndStep(Step):
  """End Event of a Diagnostic Tree"""

  def __init__(self):
    super().__init__(step_type=constants.StepType.END)

  def execute(self):
    """Finalizing runbook investigations..."""
    if not config.get(flags.INTERACTIVE_MODE):
      response = op.operator.interface.prompt(kind=op.CONFIRMATION,
                                              message='Is your issue resolved?')
      if response == op.NO:
        op.operator.interface.info(message=constants.END_MESSAGE)


class Gateway(Step):
  """
  Represents a decision point in a workflow, determining which path to take based on a condition.
  """

  def __init__(self):
    """
    Initializes a new instance of the Gateway step.
    """
    super().__init__(step_type=constants.StepType.GATEWAY)


class RunbookRule(type):
  """Metaclass for automatically registering subclasses of DiagnosticTree
  in a registry for easy lookup and instantiation based on product/rule ID."""

  def __new__(mcs, name, bases, namespace):
    new_class = super().__new__(mcs, name, bases, namespace)
    if name != 'DiagnosticTree' and bases[0] == DiagnosticTree:
      rule_id = util.runbook_name_parser(name)
      product = namespace.get('__module__', '').split('.')[-2].lower()
      RunbookRegistry[f'{product}/{rule_id}'] = new_class
    return new_class


class DiagnosticTree(metaclass=RunbookRule):
  """Represents a diagnostic tree for troubleshooting."""
  product: str
  name: str
  start: StartStep
  parameters: Dict[str, Dict]
  steps: List[Step]
  keywords: List[str]

  def __init__(self, uuid=None):
    self.id = f'{self.__module__}.{self.__class__.__name__}'
    self.uuid = uuid or util.generate_uuid()
    self.product = self.__module__.rsplit('.')[-2].lower()
    self.doc_file = util.pascal_case_to_kebab_case(self.__class__.__name__)
    self.dt_name = util.runbook_name_parser(self.__class__.__name__)
    self.name = f'{self.product}/{self.dt_name}'
    self.steps = []

  @property
  def run_id(self):
    return '.'.join([self.product, self.dt_name, self.uuid])

  def add_step(self, parent: Step, child: Step):
    """Adds an intermediate diagnostic step to the tree."""
    if self.start is None:
      raise ValueError('Start step is empty. Set start step with'
                       ' builder.add_start() or tree.add_start()')
    if parent is None:
      raise ValueError('You can\'t add a child to a `NoneType` parent')
    # to avoid disjoint trees, we first check that the parent is a child of start.
    parent_step = self.start.find_step(parent)
    if parent_step:
      parent_step.add_child(child)
    else:
      raise ValueError(
          f'Parent step with {parent.execution_id} not found. Add parent first')

  def add_start(self, step: StartStep):
    """Adds a diagnostic step to the tree."""
    if hasattr(self, 'start') and getattr(self, 'start'):
      raise ValueError('start already exist')
    self.start = step

  def add_end(self, step: EndStep):
    """Adds the default end step of this tree which is invoked iff all child steps are executed."""
    if self.start and self.start.steps:
      if self.start.steps[-1].type == constants.StepType.END:
        raise ValueError('end already exist')
    self.start.add_child(child=step)

  def find_step(self, step_id):
    return self.start.find_step(step_id)

  @final
  def hook_build_tree(self):
    try:
      self.build_tree()
    except exceptions.InvalidDiagnosticTree as err:
      logging.warning('%s: %s while constructing runbook rule: %s',
                      type(err).__name__, err, self)

    if not self.start:
      raise exceptions.InvalidDiagnosticTree(
          'The diagnostic tree is invalid because it contains any Start point')

    if not self.start.steps:
      raise exceptions.InvalidDiagnosticTree(
          'The diagnostic tree is invalid because it contains only '
          'a Start method without any intermediate steps. '
          'Please ensure your tree includes at least one intermediate step '
          'between the Start method and the end point.')
    # if the tree hasn't be concluded with an endstep.
    # Add the default step
    if self.start.steps[-1].type != constants.StepType.END:
      self.start.add_child(EndStep())

  def build_tree(self):
    """Constructs the diagnostic tree."""
    raise NotImplementedError

  def __hash__(self):
    return str(self.name).__hash__()

  def __str__(self):
    return self.name

  @property
  def long_desc(self):
    long_desc = None
    doc_lines = self.__class__.__doc__.splitlines()
    if len(doc_lines) >= 3:
      if doc_lines[1]:
        raise ValueError(
            f'Diagnostic Tree {self.__class__.__name__} has a non-empty second '
            'line in the class docstring')
      long_desc = '\n'.join(doc_lines[2:])
    return long_desc

  @property
  def short_desc(self):
    return self.__doc__.splitlines()[0]

  @property
  def doc_url(self) -> str:
    """Returns the documentation URL for the diagnostic tree."""
    return f'https://gcpdiag.dev/runbook/diagnostic-trees/{self.name}'


class Bundle:
  run_id: str
  steps: List[Step]
  parameter: models.Parameter

  def __init__(self) -> None:
    self.run_id = util.generate_uuid()
    self.steps = []


class DiagnosticEngine:
  """Loads and Executes diagnostic trees.

  This class is responsible for loading and executing diagnostic trees
  based on provided rule name. It manages the diagnostic process, from
  validating required parameters to traversing and executing diagnostic
  steps.

  Attributes:
    _dt: Optional[DiagnosticTree] The current diagnostic tree being executed.
  """

  def __init__(self) -> None:
    """Initializes the DiagnosticEngine with required managers."""
    self.interface = report.InteractionInterface(kind=config.get('interface'))
    self.finalize = False
    # tuple in the format (DiagnosticTree/Bundle, user_provided_parameter)
    self.task_queue: Deque = Deque()

  def add_task(self, new_task: Tuple):
    self.task_queue.appendleft(new_task)

  def load_tree(self, name: str) -> DiagnosticTree:
    """Loads a diagnostic tree by name ex gce/ssh.

    Attempts to retrieve a diagnostic tree registered under the given name.
    Exits the program if the tree is not found.

    Tree are registered onload of the class definition see RunbookRule metaclass

    Args:
      name: The name of the diagnostic tree to load.
    """
    try:
      # ex: product/gce-runbook
      name = util.runbook_name_parser(name)
      tree = RunbookRegistry.get(name)
      if not tree:
        raise exceptions.DiagnosticTreeNotFound
      return tree
    except exceptions.DiagnosticTreeNotFound as e:
      logging.error('%s: %s', name, e)
      raise e

  def load_steps(self, parameter: Mapping[str, Mapping],
                 steps_to_run: List) -> Bundle:
    """Loads individual steps and prepare a bundle.

    Args:
      parameter: User provided parameter
      steps_to_run: List of steps to from a bundle specification.
    """
    bundle: Bundle = Bundle()
    bundle.parameter = models.Parameter(parameter)
    for id_ in steps_to_run:
      step_def = StepRegistry.get(id_)
      if not step_def:
        logging.error('skipping step "%s": no step definition found', id_)
        continue
      bundle.steps.append(step_def)
    return bundle

  def _get_billing_project(self, parameter: models.Parameter):
    project_id = parameter.get('project_id')
    if project_id:
      return project_id
    # get project number if no project id
    project_number = parameter.get('project_number')
    if project_number:
      project = crm.get_project(project_id=project_number)
      return project.id
    if config.get('billing_project'):
      return config.get('billing_project')
    return None

  def _check_required_paramaters(self, parameter_def: Dict,
                                 caller_args: models.Parameter):
    missing_parameters = {
        key: value.get('help', '')
        for key, value in parameter_def.items()
        if value.get('required', False) and key not in caller_args
    }
    if missing_parameters:
      missing_param_str = '\n'.join(
          f'Help: {value}\n-p {key}=value\n'
          for key, value in missing_parameters.items())
      logging.error(
          'Missing %s required %s. Please provide the following:\n\n%s\nExiting program',
          len(missing_parameters),
          'parameter' if len(missing_parameters) == 1 else 'parameters',
          missing_param_str)
      raise AttributeError('missing required parameters to run runbook')

  def _set_default_parameters(self, parameter_def: Dict):
    # set default parameters
    parameter_def.setdefault(flags.START_TIME_UTC, {
        'type': datetime,
        'help': 'Beginning Timeframe to scope investigation.'
    })
    parameter_def.setdefault(flags.END_TIME_UTC, {
        'type': datetime,
        'help': 'End timeframe'
    })

  def parse_parameters(self, parameter_def: Dict,
                       caller_args: models.Parameter):
    """Set to defaults parameters and convert datatypes"""

    def is_builtin_type(target_type):
      """Check if the object's type is a built-in type."""
      return target_type in vars(builtins).values()

    def cast_to_type(param_val, target_type):
      """Attempt to cast the object to the target built-in type if possible.

      Args:
          obj: The object to cast.
          target_type: The target built-in type to cast the object to.

      Returns:
          The object cast to the target type if the original object's type and the target type are
          built-in types and the cast is possible. Otherwise, returns the original object.
      """
      if is_builtin_type(target_type) and target_type != bool:
        try:
          return target_type(param_val)
        except ValueError:
          print(f'Cannot cast {param_val} to type {target_type}.')
      elif target_type == bool:
        try:
          return constants.BOOL_VALUES[str(param_val).lower()]
        except KeyError:
          print(f'Cannot cast {param_val} to type {target_type}.')
      else:
        if target_type == datetime:
          if isinstance(param_val, target_type):
            return param_val
          parsed_time = util.parse_time_input(param_val.upper())
          if parsed_time.tzinfo is None:
            # Define the timezone (for example, UTC) if not present
            tz = timezone.utc
            # Attach the timezone information
            parsed_time = parsed_time.replace(tzinfo=tz)
          return parsed_time
        try:
          return target_type(param_val)
        except ValueError:
          print(f'Cannot cast {param_val} to type {target_type}.')

    self._set_default_parameters(parameter_def)
    # convert data types and set defaults for non exist parameters
    for k, _ in parameter_def.items():
      # Set default if not provided by user
      dt_param = parameter_def.get(k)
      user_provided_param = caller_args.get(k)
      if k not in caller_args and dt_param and dt_param.get('default'):
        caller_args[k] = dt_param['default']
        continue

      if isinstance(user_provided_param, str):
        if dt_param and dt_param.get('ignorecase') is True:
          caller_args[k] = user_provided_param
        else:
          caller_args[k] = user_provided_param.lower()

      if dt_param and dt_param.get('type') == datetime:
        if k == flags.END_TIME_UTC:
          end_time = caller_args.get(flags.END_TIME_UTC,
                                     datetime.now(timezone.utc))
          caller_args[flags.END_TIME_UTC] = cast_to_type(
              end_time, dt_param['type'])
        if k == flags.START_TIME_UTC:
          end_time = caller_args.get(flags.END_TIME_UTC,
                                     datetime.now(timezone.utc))
          caller_args[flags.END_TIME_UTC] = cast_to_type(
              end_time, dt_param['type'])
          parsed_end_time = caller_args[flags.END_TIME_UTC]
          start_time = caller_args.get(flags.START_TIME_UTC,
                                       parsed_end_time - timedelta(hours=8))
          caller_args[flags.START_TIME_UTC] = cast_to_type(
              start_time, dt_param['type'])
        if k != flags.START_TIME_UTC or k == flags.END_TIME_UTC:
          date_string = caller_args.get(k)
          if date_string:
            caller_args[k] = cast_to_type(date_string, dt_param['type'])

      # DT specified a type for the param and it's not a string.
      # cast the parameter to the type specified by the runbook.
      if (dt_param and dt_param.get('type') and dt_param['type'] != str and
          user_provided_param):
        caller_args[k] = cast_to_type(user_provided_param, dt_param['type'])

  def run(self):
    """Execute tasks (runbooks or bundles) present in the engines task queue"""
    if not self.task_queue:
      logging.error('No tasks to execute. Did you call add_task()?')
      return

    for task in self.task_queue:
      if isinstance(task[0], Bundle):
        self.run_bundle(task[0])
        continue

      if isinstance(task[0], DiagnosticTree):
        self.run_diagnostic_tree(tree=task[0], parameter=task[1])

  def run_diagnostic_tree(self, tree: DiagnosticTree,
                          parameter: models.Parameter) -> None:
    """Executes a diagnostic tree with a given parameter.

    Args:
      context: The execution context for the diagnostic tree.
    """
    self._check_required_paramaters(parameter_def=tree.parameters,
                                    caller_args=parameter)
    self.parse_parameters(parameter_def=tree.parameters, caller_args=parameter)
    self.interface.output.display_runbook_description(tree)

    try:
      operator = op.Operator(interface=self.interface)
      operator.set_tree(tree)
      operator.set_parameters(parameter)
      operator.set_run_id(tree.run_id)
      project_id = self._get_billing_project(parameter)
      operator.create_context(p=parameter, project_id=project_id)
      self.interface.rm.reports[tree.run_id] = report.Report(
          run_id=tree.run_id, parameters=parameter)
      self.interface.rm.reports[tree.run_id].run_start_time = datetime.now(
          timezone.utc).isoformat()
      if operator.tree:
        self.interface.rm.reports[tree.run_id].runbook_name = operator.tree.name
      with op.operator_context(operator):
        tree.hook_build_tree()
      self.finalize = False
      self.find_path_dfs(step=tree.start,
                         operator=operator,
                         executed_steps=set())

    except (RuntimeError, exceptions.InvalidDiagnosticTree) as err:
      logging.warning('%s: %s while processing runbook rule: %s',
                      type(err).__name__, err, tree)
    self.interface.rm.reports[tree.run_id].run_end_time = datetime.now(
        timezone.utc).isoformat()

  def find_path_dfs(self, step: Step, operator: op.Operator,
                    executed_steps: Set):
    """Depth-first search to traverse and execute steps in the diagnostic tree.

    Args:
      step: The current step to execute.
      operator: The operator used duing execution.
      executed_steps: A set of executed step IDs to avoid cycles.
    """
    if not self.finalize:
      operator.set_step(step)
      with op.operator_context(operator):
        outcome = self.run_step(step=step, operator=operator)
        executed_steps.add(step)
        if outcome == constants.FINALIZE_INVESTIGATION:
          self.finalize = True
          return
      for child in step.steps:  # Iterate over the children of the current step
        if child not in executed_steps:
          self.find_path_dfs(step=child,
                             operator=operator,
                             executed_steps=executed_steps)
      return executed_steps

  def run_step(self, step: Step, operator: op.Operator):
    """Executes a single step, handling user decisions for step re-evaluation or termination.

    Args:
      step: The diagnostic step to execute.
      operator: The execution operations object containing the context.
    """
    try:
      user_input = self._run(step, operator)
      while True:
        if user_input is constants.RETEST:
          operator.interface.info(step_type=constants.RETEST,
                                  message='Re-evaluating recent failed step')
          with caching.bypass_cache():
            user_input = self._run(operator.step, operator=operator)
        elif step.type == constants.StepType.END:
          return constants.FINALIZE_INVESTIGATION
        elif user_input is constants.STOP:
          logging.info('Finalizing Investigation\n')
          return constants.FINALIZE_INVESTIGATION
        elif step.type == constants.StepType.START and (
          self.interface.rm.reports[operator.run_id]
          .results.get(step.execution_id) is not None and \
          self.interface.rm.reports[operator.run_id]
          .results[step.execution_id].overall_status == 'skipped'):
          logging.info('Start Step was skipped. Can\'t proceed ...\n')
          return constants.FINALIZE_INVESTIGATION
        elif user_input is constants.CONTINUE:
          break
        elif (user_input is not constants.RETEST and
              user_input is not constants.CONTINUE and
              user_input is not constants.STOP):
          return user_input
    except Exception as err:  # pylint: disable=broad-exception-caught
      error_msg = str(err)
      end = datetime.now(timezone.utc).isoformat()
      self.interface.rm.reports[operator.run_id].results[
          step.execution_id].end_time = end
      if isinstance(err, TemplateNotFound):
        error_msg = (
            f'could not load messages linked to step: {step.id}.'
            'ensure step has a valid template eg: filename::block_prefix')
        logging.error(error_msg)
      elif isinstance(err, exceptions.InvalidStepOperation):
        error_msg = f'invalid step operation: %s: {err}'
        logging.error(error_msg)
      elif isinstance(err, (ValueError, KeyError)):
        error_msg = f'`{step.execution_id}`: {err}'
        logging.error(error_msg)
      elif isinstance(err,
                      (utils.GcpApiError, googleapiclient.errors.HttpError)):
        if isinstance(err, googleapiclient.errors.HttpError):
          err = utils.GcpApiError(err)
        if err.status == 403:
          logging.error(
              ('%s: %s user does not sufficient permissions '
               'to perform operations in step: %s'),
              type(err).__name__,
              err,
              step.execution_id,
          )
          return
        logging.error(
            '%s: %s while processing step: %s',
            type(err).__name__,
            err,
            step.execution_id,
        )
      else:
        logging.error(
            '%s: %s while processing step: %s',
            type(err).__name__,
            err,
            step.execution_id,
        )
      self.interface.rm.reports[operator.run_id].results[
          step.execution_id].step_error = error_msg

  def _run(self, step: Step, operator: op.Operator):
    start = datetime.now(timezone.utc).isoformat()
    self.interface.rm.reports[operator.run_id].results[
        step.execution_id] = report.StepResult(step=step)
    self.interface.rm.reports[operator.run_id].results[
        step.execution_id].start_time = start
    step.execute_hook(operator)
    end = datetime.now(timezone.utc).isoformat()
    self.interface.rm.reports[operator.run_id].results[
        step.execution_id].end_time = end
    return self.interface.rm.reports[operator.run_id].results[
        step.execution_id].prompt_response

  def run_bundle(self, bundle: Bundle) -> None:
    """Executes a list of steps present in a bundle

    Args:
      bundle: bundle to be excuted
    """
    operator = op.Operator(interface=self.interface)
    operator.set_parameters(bundle.parameter)
    operator.set_run_id(bundle.run_id)
    project_id = self._get_billing_project(bundle.parameter)
    operator.create_context(p=bundle.parameter, project_id=project_id)
    self.interface.rm.reports[bundle.run_id] = report.Report(
        run_id=bundle.run_id, parameters=bundle.parameter)
    with op.operator_context(operator):
      for step in bundle.steps:
        self._check_required_paramaters(parameter_def=step.parameters,
                                        caller_args=bundle.parameter)
        self.parse_parameters(parameter_def=step.parameters,
                              caller_args=bundle.parameter)
        if callable(step):
          step_obj = step(**bundle.parameter)
          operator.set_step(step_obj)
          self.run_step(step=step_obj, operator=operator)


class ExpandTreeFromAst(ast.NodeVisitor):
  """Builds a Diagnostic Tree by traversing the Abstract Syntax Tree

  This is required to be able to get a full flow of all possible steps
  regardless of conditions required to trigger during runtime execution.
  """

  def __init__(self, tree=None):
    self.tree = tree() or DiagnosticTree()
    self.parent = OrderedDict()
    self.current_class = None
    # Track instances to map variable names to their classes
    self.instances = {}

  # pylint: disable=invalid-name
  def visit_Assign(self, node):
    # Track class instances
    if isinstance(node.value, ast.Call) and hasattr(node.value.func, 'id'):
      for target in node.targets:
        if isinstance(target, ast.Name):
          clazz = find_class_globally(node.value.func.id)
          if not clazz:
            continue
          o = clazz() if isinstance(clazz, type) else clazz
          self.instances.setdefault(target.id, o)
          self.instances.setdefault(node.value.func.id, o)
    # Check for is there are more nesting. like gce_cs.spec.SomeStep()
    if isinstance(node.value, ast.Call) and hasattr(node.value.func, 'attr'):
      for target in node.targets:
        if isinstance(target, ast.Name):
          clazz = find_class_globally(node.value.func.attr)
          if not clazz:
            continue
          o = clazz() if isinstance(clazz, type) else clazz
          self.instances.setdefault(target.id, o)
          self.instances.setdefault(node.value.func.attr, o)
    self.generic_visit(node)

  # pylint: disable=invalid-name
  def visit_Call(self, node):
    if isinstance(node.func,
                  ast.Attribute) and node.func.attr in ('add_child', 'add_step',
                                                        'add_start', 'add_end'):
      child = None
      if len(node.args) == 1:
        node.keywords.append(ast.keyword('step', node.args[0]))
      if len(node.args) == 2:
        node.keywords.append(ast.keyword('parent', node.args[0]))
        node.keywords.append(ast.keyword('child', node.args[1]))
      if node.keywords:
        for kw in node.keywords:
          arg_name = kw.arg
          step = kw.value
          if arg_name == 'parent':
            p = find_class_globally(self.instances[step.id])
            p = p() if isinstance(p, type) else p
            self.parent.setdefault(self.instances[step.id], p)
          if arg_name in ('child', 'step'):
            if isinstance(step, ast.Name) and step.id in self.instances:
              # Map variable name to class instance if possible
              clazz = self.instances.get(step.id)
              if not clazz:
                clazz = find_class_globally(step.id)
                if not clazz:
                  continue
              clazz = clazz() if isinstance(clazz, type) else clazz
              self.instances.setdefault(step.id, clazz)
              child = clazz  # This is a direct class name
            elif isinstance(step, ast.Call) and hasattr(step.func, 'id'):
              clazz = self.instances.get(step.func.id)
              if not clazz:
                clazz = find_class_globally(step.func.id)
                if not clazz:
                  continue
              clazz = clazz() if isinstance(clazz, type) else clazz
              self.instances.setdefault(step.func.id, clazz)
              child = clazz  # This is a direct class name
            # if argument of call is instantiated directly and has module attr.
            elif isinstance(step, ast.Call) and hasattr(step.func, 'attr'):
              clazz = self.instances.get(step.func.attr)
              if not clazz:
                clazz = find_class_globally(step.func.attr)
                if not clazz:
                  continue
              clazz = clazz() if isinstance(clazz, type) else clazz
              self.instances.setdefault(step.func.attr, clazz)
              child = clazz  # This is a direct class name

      if node.func.attr in ('add_start'):
        self.tree.add_start(child)
        self.visit_ast_nodes(child.__class__)

      if node.func.attr in ('add_end'):
        self.tree.add_end(child)
        self.visit_ast_nodes(child.__class__)

      if node.func.attr in ('add_step'):
        _, p = self.parent.popitem()
        self.tree.add_step(parent=p, child=child)
        self.visit_ast_nodes(child.__class__)

      if node.func.attr in ('add_child'):
        o = self.instances.get(self.current_class)
        self.tree.add_step(parent=o, child=child)
        self.generic_visit(node)

  def visit_ClassDef(self, node):
    # Initialize or clear the list of add_child calls for this class
    self.current_class = node.name
    self.generic_visit(node)
    self.current_class = None

  def visit_ast_nodes(self, func):
    source_code = inspect.getsource(func)
    tree = ast.parse(textwrap.dedent(source_code))
    self.generic_visit(tree)
    return self.tree


def find_class_globally(class_name):
  try:
    if not isinstance(class_name, str) and isinstance(class_name, object):
      return class_name
  except TypeError:
    pass
  # First, check the current global namespace
  cls = globals().get(class_name)
  if cls:
    return cls

  # If not found, check each imported module
  for _, module in sys.modules.items():
    try:
      cls = getattr(module, class_name, None)
      if cls and inspect.isclass(cls) and issubclass(cls, Step):
        return cls
    except AttributeError:
      continue
  return None
