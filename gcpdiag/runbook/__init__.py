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

import concurrent.futures
import dataclasses
import importlib
import inspect
import json
import logging
import os
import pkgutil
import re
import sys
import textwrap
import threading
import time
import types
from collections.abc import Callable
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, Iterator, List, Optional, Protocol, Set

import blessings
import googleapiclient.errors

from gcpdiag import config, models, utils
from gcpdiag.executor import get_executor
from gcpdiag.queries import logs

OUTPUT_WIDTH = 68


@dataclasses.dataclass
class RunbookRule:
  """Identifies a runbook diagnostic flow."""
  product: str
  rule_id: str
  doc: str
  start_f: Callable
  end_f: Optional[Callable] = None
  req_params: Optional[dict] = None
  prepare_rule_f: Optional[Callable] = None
  prefetch_rule_f: Optional[Callable] = None
  prefetch_rule_future: Optional[concurrent.futures.Future] = None

  def __hash__(self):
    return str(self.product + self.rule_id).__hash__()

  def __str__(self):
    return self.product + '/' + self.rule_id

  @property
  def doc_url(self) -> str:
    return f'https://gcpdiag.dev/runbook/{self.product}/{self.rule_id}'


@dataclasses.dataclass
class RunbookNodeResult:
  """Runbook Node Results"""
  status: str
  resource: Optional[models.Resource]
  node: str
  reason: Optional[str]
  remediation: Optional[str]
  remediation_skipped: Optional[bool]

  def __init__(self,
               status: str,
               resource: Optional[models.Resource],
               node: str,
               reason: Optional[str],
               remediation: Optional[str],
               remediation_skipped: Optional[bool] = False):
    self.status = status
    self.resource = resource
    self.node = node
    self.reason = reason
    self.remediation = remediation
    self.remediation_skipped = True if config.get(
        'auto') else remediation_skipped

  def __hash__(self) -> int:
    return str(self.status + str(self.resource or '') + str(self.node) +
               (self.remediation or '') + (self.reason or '')).__hash__()

  def __eq__(self, other) -> bool:
    if self.__class__ == other.__class__:
      return (self.status == other.status and self.node == other.node and
              self.resource == other.resource and
              self.reason == other.reason and
              self.remediation == other.remediation)
    else:
      return False


class RunbookInteractionInterface:
  """
  RunbookRule workflow use this interface to report ongoing results.
  """
  rule: RunbookRule
  results: Set[RunbookNodeResult]
  _report: 'RunbookReport'
  _report_path: str
  line_unfinished: bool
  term: blessings.Terminal

  def __init__(self, rule: RunbookRule,
               runbook_report: 'RunbookReport') -> None:
    self.rule = rule
    self._report = runbook_report
    self.results = set()
    self.term = blessings.Terminal()

    date = datetime.now(timezone.utc).strftime('%Y_%m_%d_%H_%M_%S_%Z')
    report_name = f'runbook_report_{self.rule.product}_{self.rule.rule_id}_{date}.json'
    self._report_path = os.path.join(config.get('report_dir'), report_name)

  @property
  def overall_status(self) -> str:
    if self._any_result_with_status('failed'):
      return 'failed'
    elif self._any_result_with_status('ok'):
      return 'ok'
    else:
      return 'skipped'

  def _any_result_with_status(self, status: str) -> bool:
    return any(r.status == status for r in self.results)

  def add_skipped(self,
                  resource: Optional[models.Resource],
                  reason: str,
                  remediation: str = None) -> None:
    node = self.get_calling_method()

    short_path = resource.short_path if resource is not None \
                 and resource.short_path is not None else ''
    self.terminal_print_line()
    self.terminal_print_line('   - ' + short_path.ljust(OUTPUT_WIDTH) + ' [' +
                             self.term.yellow('SKIP') + ']')
    if reason:
      self.terminal_print_line('     [' + self.term.green('REASON') + ']')
      self.terminal_print_line(textwrap.indent(reason, '     '))

    if remediation:
      self.terminal_print_line('     [' + self.term.green('REMEDIATION') + ']')
      self.terminal_print_line(textwrap.indent(remediation, '     '))

    self.results.add(
        RunbookNodeResult(status='skipped',
                          resource=resource,
                          node=node,
                          reason=reason,
                          remediation=remediation))

  def add_ok(self, resource: models.Resource, reason: str = '') -> None:
    node = self.get_calling_method()
    short_path = resource.short_path if resource is not None \
                 and resource.short_path is not None else ''
    self.terminal_print_line()
    self.terminal_print_line('   - ' + short_path.ljust(OUTPUT_WIDTH) + ' [' +
                             self.term.green('OK') + ']')
    if reason:
      self.terminal_print_line('     [' + self.term.green('REASON') + ']')
      self.terminal_print_line(textwrap.indent(reason, '     '))
      self.results.add(
          RunbookNodeResult(status='ok',
                            resource=resource,
                            node=node,
                            reason=reason,
                            remediation=''))

  def get_calling_method(self):
    # add report // task
    calling_frame = inspect.currentframe().f_back.f_back.f_back.f_back
    if calling_frame:
      method_name = calling_frame.f_code.co_name
      return method_name

  def add_failed(self,
                 resource: models.Resource,
                 reason: str,
                 remediation: str,
                 human_task_msg: str = '') -> Any:
    """Output test result and registers the result to be used in
    the runbook report.

    The failure assigned a human task unless program is running
    autonomously
    """
    node = self.get_calling_method()

    short_path = resource.short_path if resource is not None \
                 and resource.short_path is not None else ''
    self.terminal_print_line()
    self.terminal_print_line('   - ' + short_path.ljust(OUTPUT_WIDTH) + ' [' +
                             self.term.red('FAIL') + ']')
    if reason:
      self.terminal_print_line('     [' + self.term.green('REASON') + ']')
      self.terminal_print_line(textwrap.indent(f'{reason}', '     '))

    if remediation:
      self.terminal_print_line('     [' + self.term.green('REMEDIATION') + ']')
      self.terminal_print_line(textwrap.indent(f'{remediation}', '     '))
      result = RunbookNodeResult(status='failed',
                                 resource=resource,
                                 reason=reason,
                                 node=node,
                                 remediation=remediation)
    self.results.add(result)
    # assign a human task to be completed
    if not config.get('auto'):
      choice = self.prompt(task=self.HUMAN_TASK, message=human_task_msg)

      if choice is self.CONTINUE or choice is self.ABORT:
        result.remediation_skipped = True
      return choice

  def add_uncertain(self,
                    resource: models.Resource,
                    reason: str,
                    remediation: str = None,
                    human_task_msg: str = '') -> None:
    node = self.get_calling_method()

    short_path = resource.short_path if resource is not None \
                 and resource.short_path is not None else ''
    self.terminal_print_line()
    self.terminal_print_line('   - ' + short_path.ljust(OUTPUT_WIDTH) + ' [' +
                             self.term.yellow('UNCERTAIN') + ']')
    if reason:
      self.terminal_print_line('     [' + self.term.green('REASON') + ']')
      self.terminal_print_line(textwrap.indent(reason, '     '))

    if remediation:
      self.terminal_print_line('     [' + self.term.green('REMEDIATION') + ']')
      self.terminal_print_line(textwrap.indent(f'{remediation}', '     '))
      result = RunbookNodeResult(status='uncertain',
                                 resource=resource,
                                 reason=reason,
                                 node=node,
                                 remediation=remediation)
    self.results.add(result)
    if not config.get('auto'):
      choice = self.prompt(task=self.HUMAN_TASK, message=human_task_msg)

      if choice is self.CONTINUE or choice is self.ABORT:
        result.remediation_skipped = True
      return choice

  def terminal_update_line(self, text: str) -> None:
    """Update the current line on the terminal."""
    if self.term.width:
      print(self.term.move_x(0) + self.term.clear_eol() + text,
            end='',
            flush=True,
            file=sys.stdout)
      self.line_unfinished = True
    else:
      # If it's a stream, do not output anything, assuming that the
      # interesting output will be passed via terminal_print_line
      pass

  def terminal_print_line(self, text: str = '') -> None:
    """Write a line to the terminal, replacing any current line content, and add a line feed."""
    if self.term.width:
      self.terminal_update_line(text)
      print(file=sys.stdout)
    else:
      print(text, file=sys.stdout)
      # flush the output, so that we can more easily grep, tee, etc.
      sys.stdout.flush()
    self.line_unfinished = False

  def generate_report(self):
    """Generate Runbook Report"""
    result = self._generate_json_report()
    if config.get('interface') == 'cli':
      self._write_report_to_terminal(result)

  def _generate_json_report(self):

    def result_to_dict(result: RunbookNodeResult):
      return {
          'node':
              result.node,
          'resource':
              result.resource.short_path if result.resource else '-',
          'status':
              result.status,
          'reason':
              result.reason,
          'remediation':
              result.remediation if result.remediation else '-',
          'remediation_skipped':
              False if config.get('auto') else result.remediation_skipped
      }

    report = {
        'runbook': f'{self.rule.product}/{self.rule.rule_id}',
        'totals_by_status': self._report.get_totals_by_status(),
        'execution_mode': 'auto' if config.get('auto') else 'interactive',
        'results': list(self.results)
    }
    return json.dumps(report,
                      ensure_ascii=False,
                      default=result_to_dict,
                      indent=2)

  def _write_report_to_terminal(self, json_report):
    try:
      with open(self._report_path, 'w', encoding='utf-8') as file:
        file.write(json_report)
    except PermissionError as e:
      logging.error(
          'Permission denied while saving report to file, displaying report')
      logging.debug(e)
      print(json_report, file=sys.stderr)
    except OSError as e:
      logging.error(
          'Failed to save generated report to file, displaying report')
      logging.debug(e)
      print(json_report, file=sys.stderr)
    else:
      print(f'\nRunbook report located in: {file.name}', file=sys.stderr)

  RETEST = 'RETEST'
  YES = 'YES'
  NO = 'NO'
  CONTINUE = 'CONTINUE'
  CONFIRMATION = 'CONFIRMATION'
  ABORT = 'ABORT'
  STEP = 'STEP'
  DECISION = 'DECISION'
  HUMAN_TASK = 'HUMAN_TASK'
  HUMAN_TASK_OPTIONS = {
      'r': 'Retest current step',
      'c': 'Continue',
      'a': 'Abort'
  }
  CONFIRMATION_OPTIONS = {'Yes/Y/y': 'Yes', 'No/N/n': 'No'}

  def prompt(self,
             message: str,
             task: str = '',
             options: dict = None,
             choice_msg: str = 'Choose an option: '):
    """
    For informational update and getting a response from user
    """
    # information prompt
    if not task:
      self.terminal_print_line(text='' + '[' + self.term.green('INFO') + ']: ' +
                               f'{message}')
      return
    # Step or decision
    if task and task in self.STEP or task in self.DECISION or \
    task in self.RETEST:
      self.terminal_print_line()
      self.terminal_print_line(text='' + '[' + self.term.green(task) + ']: ' +
                               f'{message}')
      return

    self.default_answer = False
    self.answer = None
    options_text = '\n'
    try:
      if task in self.HUMAN_TASK and not options and not config.get('auto'):
        for option, description in self.HUMAN_TASK_OPTIONS.items():
          options_text += '[' + self.term.green(
              f'{option}') + ']' + f' - {description}\n'
      if task in self.CONFIRMATION and not options\
          and not config.get('auto'):
        for option, description in self.CONFIRMATION_OPTIONS.items():
          options_text += '[' + self.term.green(
              f'{option}') + ']' + f' - {description}\n'
      if (task in self.CONFIRMATION or task in self.HUMAN_TASK) \
        and options and not config.get('auto'):
        for option, description in options.items():
          options_text += '[' + self.term.green(
              f'{option}') + ']' + f' - {description}\n'
      #TODO: allow to get special data. ex ip or just an error
      if not config.get('auto'):
        if message:
          self.terminal_print_line(text=textwrap.indent(message, '     '))
        if options_text:
          self.terminal_print_line(text=textwrap.indent(options_text, '     '))
          self.answer = input(textwrap.indent(choice_msg, '     '))
    except EOFError:
      return self.answer
    # pylint:disable=g-explicit-bool-comparison, We explicitly want to
    # distinguish between empty string and None.
    if self.answer == '':
      # User just hit enter, return default.
      return self.default_answer
    elif self.answer is None:
      return self.answer
    elif self.answer.strip().lower() in ['a', 'abort']:
      return self.ABORT
    elif self.answer.strip().lower() in ['c', 'continue']:
      return self.CONTINUE
    elif self.answer.strip().lower() in ['r', 'retest']:
      return self.RETEST
    elif self.answer.strip().lower() in ['y', 'yes']:
      return self.YES
    elif self.answer.strip().lower() in ['n', 'no']:
      return self.NO
    elif self.answer.strip().lower() not in [
        'a', 'abort', 'c', 'continue', 'r', 'retest'
    ]:
      return self.answer.strip()
    return

  def execute_task(self, task: Callable):
    # First execution of the node task
    choice = task()
    while True:
      if choice is self.RETEST:
        self.prompt(task=self.RETEST, message='Reevaluating Task.')
        choice = task()
      if choice is self.CONTINUE:
        return choice
      if choice is self.ABORT:
        logging.info('Terminating Runbook\n')
        sys.exit(2)
      elif choice is not self.RETEST and choice is not self.CONTINUE and choice is not self.ABORT:
        return choice


class RunbookResultsHandler(Protocol):
  """
  Protocol representing object capable of handling runbook results (handlers).
  Hanlders can be registered with RunbookResults and react on each rule added
  to the RunbookResults: each time a rule is added to the RunbookResults
  process_rule_report method of each registered handler is called with
  RunbookInteractionInterface, so that handler have access to the results of
  the rule execution.
  """

  def process_rule_report(self,
                          rule_report: RunbookInteractionInterface) -> None:
    pass


class RunbookReport:
  """ Class representing results of runbook """
  _result_handlers: List[RunbookResultsHandler]
  _rule_reports: List[RunbookInteractionInterface]

  def __init__(self) -> None:
    self._result_handlers = []
    self._rule_reports = []

  def add_result_handler(self, handler: RunbookResultsHandler) -> None:
    """
    Hanlders can be registered with RunbookResults and react on each rule added
    to the RunbookResults: each time a rule is added to the RunbookResults
    process_rule_report method of each registered handler is called with
    RunbookInteractionInterface, so that handler have access to the results of
    the rule execution.
    """
    self._result_handlers.append(handler)

  def create_rule_report(self,
                         rule: RunbookRule) -> RunbookInteractionInterface:
    report = RunbookInteractionInterface(rule=rule, runbook_report=self)
    term = blessings.Terminal()
    self._rule_reports.append(report)
    report.terminal_print_line('' +
                               term.yellow(f'{rule.product}/{rule.rule_id}') +
                               ': ' + f'{rule.doc}')
    return report

  def get_totals_by_status(self) -> Dict[str, int]:
    totals: Dict[str, int]
    totals = {}
    for rule_report in self._rule_reports:
      for node_result in rule_report.results:
        totals[node_result.status] = totals.get(node_result.status, 0) + 1
    return totals

  def get_rule_statuses(self) -> Dict[str, str]:
    return {str(r.rule): r.overall_status for r in self._rule_reports}

  @property
  def any_failed(self) -> bool:
    return any(r.overall_status == 'failed' for r in self._rule_reports)


class RunbookRulesPattern:
  """Filter to select rules to run.

  RunbookRule patterns are written with the following
  format: PRODUCT/ID, e.g. gke/missing-logs.
  """

  product: Optional[str]
  rule_id: Optional[re.Pattern]

  def __init__(self, pattern_str: str):
    self.product = None
    self.rule_id = None

    m = re.match(r'^([a-z]+)/([a-z/-]+)$', pattern_str, re.IGNORECASE)
    if m:
      self.product = m.group(1)
      self.rule_id = re.compile(m.group(2), re.IGNORECASE)

    else:
      raise ValueError(
          f"""rule pattern doesn't look like a valid pattern: {pattern_str}
              use: gcpdiag runbook product/runbook-id""")

  def __str__(self):
    # pylint: disable=consider-using-f-string
    return '{}/{}'.format(self.product or '*', self.rule_id or '*')

  def match_rule(self, rule: RunbookRule) -> bool:
    if self.product:
      if self.product != rule.product:
        return False
    if self.rule_id:
      if not self.rule_id.match(rule.rule_id):
        return False
    return True


class NotRunbookRule(Exception):
  pass


# pylint: disable=unsubscriptable-object
def is_function_named(name: str) -> Callable[[Any], bool]:
  return lambda obj: inspect.isfunction(obj) and obj.__name__ == name


def get_module_function_or_none(module: types.ModuleType,
                                name: str) -> Optional[Callable]:
  members = inspect.getmembers(module, is_function_named(name))
  assert 0 <= len(members) <= 1
  return None if len(members) < 1 else members[0][1]


def get_module_attr_or_none(module: types.ModuleType,
                            name: str) -> Optional[Any]:
  members = inspect.getattr_static(module, name)
  return members


class ExecutionStrategy(Protocol):

  def execute(self, context: models.Context, result: RunbookReport,
              rules: Iterable[RunbookRule]) -> None:
    pass

  def filter_runnable_rules(
      self, rules: Iterable[RunbookRule]) -> Iterable[RunbookRule]:
    pass


class RuleModule:
  """ Encapsulate actions related to a specific python rule module """
  _module: types.ModuleType

  def __init__(self, python_module: types.ModuleType) -> None:
    self._module = python_module

  def get_attr(self, attr_name: str):
    return get_module_attr_or_none(self._module, attr_name)

  def get_method(self, method_name: str) -> Optional[Callable]:
    return get_module_function_or_none(self._module, method_name)

  def get_module_doc(self) -> Optional[str]:
    return inspect.getdoc(self._module)


class DefaultPythonModulesGateway:
  """ Encapsulate actions related to python rule modules """

  def list_pkg_modules(self, pkg: Any) -> List[str]:
    prefix = pkg.__name__ + '.'
    return [p[1] for p in pkgutil.iter_modules(pkg.__path__, prefix)]

  def get_module(self, name: str) -> RuleModule:
    python_module = importlib.import_module(name)
    return RuleModule(python_module)


class PythonModulesGateway(Protocol):

  def list_pkg_modules(self, pkg: Any) -> Iterable[str]:
    pass

  def get_module(self, name: str) -> RuleModule:
    pass


def wrap_prefetch_rule_f(rule_name, prefetch_rule_f, context):
  logging.debug('prefetch_rule_f: %s', rule_name)
  thread = threading.current_thread()
  thread.name = f'prefetch_rule_f:{rule_name}'
  prefetch_rule_f(context)


class WorkflowEngine:
  """ Execute rules using thread pool """

  def filter_runnable_rules(self,
                            rules: Iterable[RunbookRule]) -> List[RunbookRule]:
    return [r for r in rules if r.start_f is not None]

  def execute(self, context: models.Context, report: RunbookReport,
              runbooks_to_run: Iterable[RunbookRule]) -> None:

    # Run the "prepare_rule" functions first, in a single thread.
    for runbook in runbooks_to_run:
      if runbook.prepare_rule_f:
        runbook.prepare_rule_f(context)

    # Start multiple threads for logs fetching and prefetch function.
    executor = get_executor()
    # Start fetching any logs queries that were defined in prepare_rule
    # functions.
    logs.execute_queries(executor)

    # Run the "prefetch_rule" functions with multiple worker threads to speed up
    # execution of the "run_rule" executions later.
    for runbook in runbooks_to_run:
      if runbook.prefetch_rule_f:
        runbook.prefetch_rule_future = executor.submit(wrap_prefetch_rule_f,
                                                       str(runbook),
                                                       runbook.prefetch_rule_f,
                                                       context)

    # While the prefetch_rule functions are still being executed in multiple
    # threads, start executing the rules, but block and wait in case the
    # prefetch for a specific rule is still running.
    last_threads_dump = time.time()
    for runbook in runbooks_to_run:
      # Check params
      if runbook.req_params:
        missing_param = {
            key: value
            for key, value in runbook.req_params.items()
            if key not in context.parameters
        }
        if missing_param:
          logging.error(
              'Required paramter(s): `%s` not provided. Exiting program',
              ' and '.join(iter(missing_param.keys())))
          sys.exit(2)
      rule_report = report.create_rule_report(runbook)
      try:
        if runbook.prefetch_rule_future:
          if runbook.prefetch_rule_future.running():
            logging.info('waiting for query results (%s)', runbook)
          while True:
            try:
              runbook.prefetch_rule_future.result(10)
              break
            except concurrent.futures.TimeoutError:
              pass
            if config.get('verbose') >= 2:
              now = time.time()
              if now - last_threads_dump > 10:
                logging.debug(
                    'THREADS: %s',
                    ', '.join([t.name for t in threading.enumerate()]))
                last_threads_dump = now
        assert runbook.start_f is not None
        node = runbook.start_f
        # determine next step
        while callable(node):
          rule_report.prompt(task=rule_report.STEP,
                             message=node.__doc__ or
                             node.__name__.replace('_', ' '))
          node = node(context, rule_report)
        else:
          if runbook.end_f:
            runbook.end_f(context, rule_report)
          else:
            if not config.get('auto'):
              response = self.prompt(task=self.CONFIRMATION,
                                     message='Is you issue resolved?')
              if response == self.NO:
                self.prompt(message=(
                    'Contact Google Cloud Support for further investigation.\n'
                    'https://cloud.google.com/support/docs/customer-care-procedures\n'
                    'Recommended: Submit the generated report to Google cloud support '
                    'when opening a ticket.'))
                rule_report.generate_report()

      except (utils.GcpApiError, googleapiclient.errors.HttpError, RuntimeError,
              ValueError, KeyError) as err:
        if isinstance(err, googleapiclient.errors.HttpError):
          err = utils.GcpApiError(err)
        logging.warning('%s: %s while processing runbook rule: %s',
                        type(err).__name__, err, runbook)
        rule_report.add_skipped(None, f'API error: {err}', None)


class RunbookRuleRepository:
  """Repository of runbook rule which is also used to run the rules."""
  rules: List[RunbookRule]
  workflow_engine: WorkflowEngine
  modules_gateway: PythonModulesGateway
  _loaded_rules: List[RunbookRule]

  def __init__(self,
               modules_gateway: Optional[PythonModulesGateway] = None,
               runbook: Iterable[RunbookRulesPattern] = None) -> None:
    self._runbook = runbook
    self._loaded_rules = []
    self.workflow_engine = WorkflowEngine()
    self.modules_gateway = modules_gateway or DefaultPythonModulesGateway()
    self.report = RunbookReport()

  @property
  def rules_to_run(self) -> Iterable[RunbookRule]:
    rules_filtered = list(self._rules_filtered())
    return self.workflow_engine.filter_runnable_rules(rules_filtered)

  def _rules_filtered(self) -> Iterator[RunbookRule]:
    runbook = self._runbook
    for rule in self._loaded_rules:
      if runbook:
        if not any(x.match_rule(rule) for x in runbook):
          continue
      yield rule

  def get_rule_by_module_name(self, name: str) -> RunbookRule:
    # Skip code tests
    if name.endswith(('_test', 'output')) or 'util' in name:
      raise NotRunbookRule()

    # Determine runbook Rule parameters based on the module name.
    m = re.search(r'\w+.\w+.(?P<product>\w+)\.(?P<rule_id>\w+)', name,
                  re.VERBOSE)
    if not m:
      # Assume this is not a rule (e.g. could be a "utility" module)
      raise NotRunbookRule()

    product, rule_id = m.group('product', 'rule_id')

    module = self.modules_gateway.get_module(name)

    # Get a reference to the execute() function.
    start_f = module.get_method('start')
    end_f = module.get_method('end')
    # Perform any prechecks relevant to the runbook
    # ex: check for missint params and give alteratives.
    req_param = dict(module.get_attr('REQUIRED_PARAMETERS'))

    if not start_f:
      raise RuntimeError(f'module {module} doesn\'t have a start function')

    # Get a reference to the prepare_rule() function.
    prepare_rule_f = module.get_method('prepare_rule')

    # Get a reference to the prefetch_rule() function.
    prefetch_rule_f = module.get_method('prefetch_rule')

    # Get module docstring.
    doc = module.get_module_doc()
    if not doc:
      raise RuntimeError(f'module {module} doesn\'t provide a module docstring')

    # Instantiate the RunbookRule object and register it
    rule = RunbookRule(product=product,
                       rule_id=rule_id,
                       start_f=start_f,
                       end_f=end_f,
                       req_params=req_param,
                       prepare_rule_f=prepare_rule_f,
                       prefetch_rule_f=prefetch_rule_f,
                       doc=doc)
    return rule

  def load_rules(self, pkg: types.ModuleType) -> None:
    for name in self.modules_gateway.list_pkg_modules(pkg):
      try:
        rule = self.get_rule_by_module_name(name)
      except NotRunbookRule:
        continue

      self._register_rule(rule)

  def _register_rule(self, rule: RunbookRule):
    self._loaded_rules.append(rule)

  def run_rules(self, context: models.Context) -> None:
    # Make sure the rules are sorted alphabetically
    self._loaded_rules.sort(key=str)
    rules_to_run = self.rules_to_run
    self.workflow_engine.execute(context, self.report, rules_to_run)
