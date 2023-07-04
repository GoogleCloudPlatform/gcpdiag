# Copyright 2021 Google LLC
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

# Lint as: python3
"""lint command: find potential issues in GCP projects."""

import abc
import asyncio
import concurrent.futures
import dataclasses
import enum
import importlib
import inspect
import logging
import os
import pkgutil
import re
import sys
import threading
import time
import types
from collections.abc import Callable
from typing import Any, Dict, Iterable, Iterator, List, Optional, Protocol, Set

import googleapiclient.errors

from gcpdiag import config, models, utils
from gcpdiag.executor import get_executor
# to avoid confusion with gcpdiag.lint.gce
from gcpdiag.queries import gce as gce_mod
from gcpdiag.queries import logs


class LintRuleClass(enum.Enum):
  """Identifies rule class."""
  ERR = 'ERR'
  BP = 'BP'
  SEC = 'SEC'
  WARN = 'WARN'
  # classes for extended rules
  ERR_EXT = 'ERR_EXT'
  BP_EXT = 'BP_EXT'
  SEC_EXT = 'SEC_EXT'
  WARN_EXT = 'WARN_EXT'

  def __str__(self):
    return str(self.value)


@dataclasses.dataclass
class LintRule:
  """Identifies a lint rule."""
  product: str
  rule_class: LintRuleClass
  rule_id: str
  short_desc: str
  long_desc: Optional[str]
  run_rule_f: Optional[Callable] = None
  async_run_rule_f: Optional[Callable] = None
  prepare_rule_f: Optional[Callable] = None
  prefetch_rule_f: Optional[Callable] = None
  prefetch_rule_future: Optional[concurrent.futures.Future] = None

  def __hash__(self):
    return str(self.product + self.rule_class.value + self.rule_id).__hash__()

  def __str__(self):
    return self.product + '/' + self.rule_class.value + '/' + self.rule_id

  @property
  def doc_url(self) -> str:
    return f'https://gcpdiag.dev/rules/{self.product}/{self.rule_class}/{self.rule_id}'


@dataclasses.dataclass
class LintRuleResult:
  status: str
  resource: Optional[models.Resource]
  reason: Optional[str]
  short_info: Optional[str]


class LintReportRuleInterface:
  """LintRule objects use this interface to report their results."""
  rule: LintRule
  results: List[LintRuleResult]
  _lint_result: 'LintResults'

  def __init__(self, rule: LintRule, lint_result: 'LintResults') -> None:
    self.rule = rule
    self._lint_result = lint_result
    self.results = []

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
                  short_info: str = None) -> None:
    self.results.append(
        LintRuleResult(status='skipped',
                       resource=resource,
                       reason=reason,
                       short_info=short_info))

  def add_ok(self, resource: models.Resource, short_info: str = '') -> None:
    self.results.append(
        LintRuleResult(status='ok',
                       resource=resource,
                       reason=None,
                       short_info=short_info))

  def add_failed(self,
                 resource: models.Resource,
                 reason: str = None,
                 short_info: str = None) -> None:
    self.results.append(
        LintRuleResult(status='failed',
                       resource=resource,
                       reason=reason,
                       short_info=short_info))

  def finish(self) -> None:
    self._lint_result.register_finished_rule_report(self)


class LintResultsHandler(Protocol):
  """
  Protocol representing object capable of handling lint results (handlers).
  Hanlders can be registered with LintResults and react on each rule added
  to the LintResults: each time a rule is added to the LintResults
  process_rule_report method of each registered handler is called with
  LintReportRuleInterface, so that handler have access to the results of
  the rule execution.
  """

  def process_rule_report(self, rule_report: LintReportRuleInterface) -> None:
    pass


class LintResults:
  """ Class representing results of lint """
  _result_handlers: List[LintResultsHandler]
  _rule_reports: List[LintReportRuleInterface]

  def __init__(self) -> None:
    self._result_handlers = []
    self._rule_reports = []

  def add_result_handler(self, handler: LintResultsHandler) -> None:
    """
    Hanlders can be registered with LintResults and react on each rule added
    to the LintResults: each time a rule is added to theLintResults
    process_rule_report method of each registered handler is called with
    LintReportRuleInterface, so that handler have access to the results of
    the rule execution.
    """
    self._result_handlers.append(handler)

  def create_rule_report(self, rule: LintRule) -> LintReportRuleInterface:
    return LintReportRuleInterface(rule=rule, lint_result=self)

  def register_finished_rule_report(
      self, rule_report: LintReportRuleInterface) -> None:
    self._rule_reports.append(rule_report)
    self._notify_result_handlers(rule_report)

  def _notify_result_handlers(self,
                              rule_report: LintReportRuleInterface) -> None:
    for handler in self._result_handlers:
      handler.process_rule_report(rule_report)

  def get_totals_by_status(self) -> Dict[str, int]:
    totals: Dict[str, int]
    totals = {}
    for rule_report in self._rule_reports:
      totals[rule_report.overall_status] = totals.get(
          rule_report.overall_status, 0) + 1
    return totals

  def get_rule_statuses(self) -> Dict[str, str]:
    return {str(r.rule): r.overall_status for r in self._rule_reports}

  @property
  def any_failed(self) -> bool:
    return any(r.overall_status == 'failed' for r in self._rule_reports)


class LintRulesPattern:
  """Filter to include/exclude rules to run.

  Rule inclusion/exclusion patterns are written with the following
  format: PRODUCT/CLASS/ID, e.g. gke/WARN/2021_001.

  `*` can be used as a wildcard:
  - `gke/*` for all gke rules
  - `gke/WARN/*` for all GKE WARN rules
  - `gke/WARN/2021_*` for all GKE WARN rules written in 2021
  - `*/WARN/*` for all WARN rules, for any product

  Additionally, you can also write just a product like `gke` or
  a rule class like `WARN`.
  """

  product: Optional[str]
  rule_class: Optional[LintRuleClass]
  rule_id: Optional[re.Pattern]

  def __init__(self, pattern_str: str):
    self.product = None
    self.rule_class = None
    self.rule_id = None

    pattern_elems = pattern_str.split('/')
    if len(pattern_elems) == 1:
      # if there are no '/', assume this is either a product name
      # or a rule class.
      if pattern_str == '*':
        pass
      elif pattern_str.upper() in LintRuleClass.__members__:
        self.rule_class = LintRuleClass(pattern_str.upper())
      else:
        self.product = pattern_str
    elif 1 < len(pattern_elems) <= 3:
      # product
      if pattern_elems[0] != '' and pattern_elems[0] != '*':
        self.product = pattern_elems[0]
      # rule class
      if pattern_elems[1] != '' and pattern_elems[1] != '*':
        self.rule_class = LintRuleClass(pattern_elems[1].upper())
      # rule id
      if len(pattern_elems) == 3:
        # convert wildcard match to regex pattern
        self.rule_id = re.compile(re.sub(r'\*', '.*', pattern_elems[2]))
    else:
      raise ValueError(
          f"rule pattern doesn't look like a pattern: {pattern_str}")

  def __str__(self):
    # pylint: disable=consider-using-f-string
    return '{}/{}/{}'.format(self.product or '*', self.rule_class or '*',
                             self.rule_id or '*')

  def match_rule(self, rule: LintRule) -> bool:
    if self.product:
      if self.product != rule.product:
        return False
    if self.rule_class:
      if self.rule_class != rule.rule_class:
        return False
    if self.rule_id:
      if not self.rule_id.match(rule.rule_id):
        return False
    return True


class NotLintRule(Exception):
  pass


# pylint: disable=unsubscriptable-object
def is_function_named(name: str) -> Callable[[Any], bool]:
  return lambda obj: inspect.isfunction(obj) and obj.__name__ == name


def get_module_function_or_none(module: types.ModuleType,
                                name: str) -> Optional[Callable]:
  members = inspect.getmembers(module, is_function_named(name))
  assert 0 <= len(members) <= 1
  return None if len(members) < 1 else members[0][1]


class ExecutionStrategy(Protocol):

  def run_rules(self, context: models.Context, result: LintResults,
                rules: Iterable[LintRule]) -> None:
    pass

  def filter_runnable_rules(self,
                            rules: Iterable[LintRule]) -> Iterable[LintRule]:
    pass


class SequentialExecutionStrategy:
  """
  Execution strategy that groups multiple execution strageties
  and runs them sequentially one after another.
  """
  strategies: List[ExecutionStrategy]

  def __init__(self, strategies: List[ExecutionStrategy]) -> None:
    self.strategies = strategies

  def filter_runnable_rules(self, rules: Iterable[LintRule]) -> List[LintRule]:
    runnable_rules: Set[LintRule]
    runnable_rules = set()
    for strategy in self.strategies:
      runnable_rules = runnable_rules.union(
          strategy.filter_runnable_rules(rules))
    return list(runnable_rules)

  def run_rules(self, context: models.Context, result: LintResults,
                rules: Iterable[LintRule]) -> None:
    for strategy in self.strategies:
      strategy.run_rules(context, result, rules)


class RuleModule:
  """ Encapsulate actions related to a specific python rule module """
  _module: types.ModuleType

  def __init__(self, python_module: types.ModuleType) -> None:
    self._module = python_module

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


def pick_default_execution_strategy(run_async: bool) -> ExecutionStrategy:
  if run_async:
    return SequentialExecutionStrategy(
        strategies=[SyncExecutionStrategy(),
                    AsyncExecutionStrategy()])
  else:
    return SyncExecutionStrategy()


class LintRuleRepository:
  """Repository of Lint rule which is also used to run the rules."""
  rules: List[LintRule]
  execution_strategy: ExecutionStrategy
  modules_gateway: PythonModulesGateway
  _loaded_rules: List[LintRule]

  def __init__(self,
               load_extended: bool = False,
               run_async: bool = False,
               execution_strategy: ExecutionStrategy = None,
               modules_gateway: Optional[PythonModulesGateway] = None,
               include: Iterable[LintRulesPattern] = None,
               exclude: Iterable[LintRulesPattern] = None) -> None:
    self._exclude = exclude
    self._include = include
    self._loaded_rules = []
    self.load_extended = load_extended
    self.execution_strategy = execution_strategy or pick_default_execution_strategy(
        run_async)
    self.modules_gateway = modules_gateway or DefaultPythonModulesGateway()
    self.result = LintResults()

  @property
  def rules_to_run(self) -> Iterable[LintRule]:
    rules_filtered = list(self._rules_filtered())
    return self.execution_strategy.filter_runnable_rules(rules_filtered)

  def _rules_filtered(self) -> Iterator[LintRule]:
    exclude = self._exclude
    include = self._include
    for rule in self._loaded_rules:
      if include:
        if not any(x.match_rule(rule) for x in include):
          continue
      if exclude:
        if any(x.match_rule(rule) for x in exclude):
          continue
      yield rule

  def get_rule_by_module_name(self, name: str) -> LintRule:
    # Skip code tests
    if name.endswith('_test'):
      raise NotLintRule()

    # Determine Lint Rule parameters based on the module name.
    m = re.search(
        r"""
         \.
         (?P<product>[^\.]+)                 # product path, e.g.: .gke.
         \.
         (?P<class_prefix>[a-z]+(?:_ext)?)   # class prefix, e.g.: 'err_' or 'err_ext'
         _
         (?P<rule_id>\d+_\d+)                # id: 2020_001
      """, name, re.VERBOSE)
    if not m:
      # Assume this is not a rule (e.g. could be a "utility" module)
      raise NotLintRule()

    product, rule_class, rule_id = m.group('product', 'class_prefix', 'rule_id')

    module = self.modules_gateway.get_module(name)

    # Get a reference to the run_rule() function.
    run_rule_f = module.get_method('run_rule')

    # Get a reference to the async_run_rule() function.
    async_run_rule_f = module.get_method('async_run_rule')

    if not (run_rule_f or async_run_rule_f):
      raise RuntimeError(
          f'module {module} doesn\'t have a run_rule or an async_run_rule function'
      )

    # Get a reference to the prepare_rule() function.
    prepare_rule_f = module.get_method('prepare_rule')

    # Get a reference to the prefetch_rule() function.
    prefetch_rule_f = module.get_method('prefetch_rule')

    # Get module docstring.
    doc = module.get_module_doc()
    if not doc:
      raise RuntimeError(f'module {module} doesn\'t provide a module docstring')
    # The first line is the short "good state description"
    doc_lines = doc.splitlines()
    short_desc = doc_lines[0]
    long_desc = None
    if len(doc_lines) >= 3:
      if doc_lines[1]:
        raise RuntimeError(
            f'module {module} has a non-empty second line in the module docstring'
        )
      long_desc = '\n'.join(doc_lines[2:])

    # Instantiate the LintRule object and register it
    rule = LintRule(product=product,
                    rule_class=LintRuleClass(rule_class.upper()),
                    rule_id=rule_id,
                    run_rule_f=run_rule_f,
                    async_run_rule_f=async_run_rule_f,
                    prepare_rule_f=prepare_rule_f,
                    prefetch_rule_f=prefetch_rule_f,
                    short_desc=short_desc,
                    long_desc=long_desc)
    return rule

  def load_rules(self, pkg: types.ModuleType) -> None:
    for name in self.modules_gateway.list_pkg_modules(pkg):
      try:
        if '_ext_' in name and not self.load_extended:
          continue
        rule = self.get_rule_by_module_name(name)
      except NotLintRule:
        continue

      self._register_rule(rule)

  def _register_rule(self, rule: LintRule):
    self._loaded_rules.append(rule)

  def run_rules(self, context: models.Context) -> None:
    # Make sure the rules are sorted alphabetically
    self._loaded_rules.sort(key=str)
    rules_to_run = self.rules_to_run
    self.execution_strategy.run_rules(context, self.result, rules_to_run)


class AsyncRunner:
  """ Helper class to represent single execution operation """

  def __init__(self, context: models.Context, result: LintResults,
               rules: Iterable[LintRule]):
    self._context = context
    self._result = result
    self._rules = rules

  def run(self) -> None:
    asyncio.run(self._run_all())

  async def _run_all(self) -> None:
    awaitables = [self._run_async_rule(r) for r in self._rules]
    await asyncio.gather(*awaitables)

  async def _run_async_rule(self, rule: LintRule) -> None:
    rule_report = self._result.create_rule_report(rule)
    assert rule.async_run_rule_f is not None
    await rule.async_run_rule_f(self._context, rule_report)
    rule_report.finish()


class AsyncExecutionStrategy:
  """ Execute async rules """

  def run_rules(self, context: models.Context, result: LintResults,
                rules: Iterable[LintRule]) -> None:
    rules = self.filter_runnable_rules(rules)
    AsyncRunner(context, result, rules).run()

  def filter_runnable_rules(self, rules: Iterable[LintRule]) -> List[LintRule]:
    return [r for r in rules if r.async_run_rule_f]


def wrap_prefetch_rule_f(rule_name, prefetch_rule_f, context):
  logging.debug('prefetch_rule_f: %s', rule_name)
  thread = threading.current_thread()
  thread.name = f'prefetch_rule_f:{rule_name}'
  prefetch_rule_f(context)


class SyncExecutionStrategy:
  """ Execute rules using thread pool """

  def filter_runnable_rules(self, rules: Iterable[LintRule]) -> List[LintRule]:
    return [r for r in rules if r.run_rule_f]

  def run_rules(self, context: models.Context, result: LintResults,
                rules: Iterable[LintRule]) -> None:

    rules_to_run = self.filter_runnable_rules(rules)

    # Run the "prepare_rule" functions first, in a single thread.
    for rule in rules_to_run:
      if rule.prepare_rule_f:
        logging.debug('prepare_rule_f: %s', rule)
        rule.prepare_rule_f(context)

    # Start multiple threads for logs fetching and prefetch functions.
    executor = get_executor()
    # Start fetching any logs queries that were defined in prepare_rule
    # functions.
    logs.execute_queries(executor)
    # Start fetching any serial output logs if serial ouput to cloud logging
    # is not enabled on the project/ instance
    if config.get('enable_gce_serial_buffer'):
      # execute fetech job
      gce_mod.execute_fetch_serial_port_outputs(executor)

    # Run the "prefetch_rule" functions with multiple worker threads to speed up
    # execution of the "run_rule" executions later.
    for rule in rules_to_run:
      if rule.prefetch_rule_f:
        rule.prefetch_rule_future = executor.submit(wrap_prefetch_rule_f,
                                                    str(rule),
                                                    rule.prefetch_rule_f,
                                                    context)

    # While the prefetch_rule functions are still being executed in multiple
    # threads, start executing the rules, but block and wait in case the
    # prefetch for a specific rule is still running.
    last_threads_dump = time.time()
    for rule in rules_to_run:
      rule_report = result.create_rule_report(rule)

      # make sure prefetch_rule_f completed
      try:
        if rule.prefetch_rule_future:
          if rule.prefetch_rule_future.running():
            logging.info('waiting for query results (%s)', rule)
          while True:
            try:
              rule.prefetch_rule_future.result(10)
              break
            except TimeoutError:
              pass
            if config.get('verbose') >= 2:
              now = time.time()
              if now - last_threads_dump > 10:
                logging.debug(
                    'THREADS: %s',
                    ', '.join([t.name for t in threading.enumerate()]))
                last_threads_dump = now
        # run the rule
        assert rule.run_rule_f is not None
        rule.run_rule_f(context, rule_report)
      except (utils.GcpApiError, googleapiclient.errors.HttpError) as err:
        if isinstance(err, googleapiclient.errors.HttpError):
          err = utils.GcpApiError(err)
        logging.warning('%s: %s while processing rule: %s',
                        type(err).__name__, err, rule)
        rule_report.add_skipped(None, f'API error: {err}', None)
      except (RuntimeError, ValueError, KeyError) as err:
        logging.warning('%s: %s while processing rule: %s',
                        type(err).__name__, err, rule)
        rule_report.add_skipped(None, f'Error: {err}', None)
      rule_report.finish()
