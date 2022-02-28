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
import concurrent.futures
import dataclasses
import enum
import importlib
import inspect
import logging
import pkgutil
import re
from collections.abc import Callable
from typing import Any, Dict, Iterable, Iterator, List, Optional

import googleapiclient.errors

from gcpdiag import models, utils
from gcpdiag.executor import get_executor
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
  long_desc: str
  run_rule_f: Callable
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


class LintReport:
  """Represent a lint report, which can be terminal-based, or (in the future) JSON."""

  rules_report: Dict[LintRule, Dict[str, Any]]

  def __init__(self):
    self.rules_report = {}

  def rule_start(self, rule: LintRule, context: models.Context):
    """Called when a rule run is started with a context."""
    return LintReportRuleInterface(self, rule, context)

  def rule_end(self, rule: LintRule, context: models.Context):
    """Called when the rule is finished running."""
    pass

  @abc.abstractmethod
  def add_skipped(self, rule: LintRule, context: models.Context,
                  resource: Optional[models.Resource], reason: str,
                  short_info: Optional[str]):
    self.rules_report.setdefault(rule, {'overall_status': 'skipped'})

  @abc.abstractmethod
  def add_ok(self, rule: LintRule, context: models.Context,
             resource: models.Resource, short_info: Optional[str]):
    rreport = self.rules_report.setdefault(rule, {'overall_status': 'ok'})
    if rreport['overall_status'] == 'skipped':
      rreport['overall_status'] = 'ok'

  @abc.abstractmethod
  def add_failed(self, rule: LintRule, context: models.Context,
                 resource: models.Resource, reason: Optional[str],
                 short_info: Optional[str]):
    rreport = self.rules_report.setdefault(rule, {'overall_status': 'ok'})
    if rreport['overall_status'] in ['skipped', 'ok']:
      rreport['overall_status'] = 'failed'

  def finish(self, context: models.Context) -> int:
    """Report that the execution of the lint rules has finished.

    The return value is the recommended exit value for the main script.
    """
    del context
    # did any rule fail? Then exit with 2, otherwise 0.
    # note: we don't use 1 because that's already the exit code when the script
    # exits with an exception.
    if any(r['overall_status'] == 'failed' for r in self.rules_report.values()):
      return 2
    return 0


class LintReportRuleInterface:
  """LintRule objects use this interface to report their results."""

  def __init__(self, report: LintReport, rule: LintRule,
               context: models.Context):
    self.report = report
    self.rule = rule
    self.context = context

  def add_skipped(self,
                  resource: Optional[models.Resource],
                  reason: str,
                  short_info: str = None):
    self.report.add_skipped(self.rule, self.context, resource, reason,
                            short_info)

  def add_ok(self, resource: models.Resource, short_info: str = ''):
    self.report.add_ok(self.rule, self.context, resource, short_info)

  def add_failed(self,
                 resource: models.Resource,
                 reason: str = None,
                 short_info: str = None):
    self.report.add_failed(self.rule, self.context, resource, reason,
                           short_info)


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


class LintRuleRepository:
  """Repository of Lint rule which is also used to run the rules."""
  rules: List[LintRule]

  def __init__(self, load_extended: bool = False):
    self.rules = []
    self.load_extended = load_extended

  def register_rule(self, rule: LintRule):
    self.rules.append(rule)

  @staticmethod
  def _iter_namespace(ns_pkg):
    prefix = ns_pkg.__name__ + '.'
    for p in pkgutil.iter_modules(ns_pkg.__path__, prefix):
      yield p[1]

  def get_rule_by_module_name(self, name):
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

    # Import the module.
    module = importlib.import_module(name)

    # Get a reference to the run_rule() function.
    run_rule_f = None
    for f_name, f in inspect.getmembers(module, inspect.isfunction):
      if f_name == 'run_rule':
        run_rule_f = f
        break
    if not run_rule_f:
      raise RuntimeError(f'module {module} doesn\'t have a run_rule function')

    # Get a reference to the prepare_rule() function.
    prepare_rule_f = None
    for f_name, f in inspect.getmembers(module, inspect.isfunction):
      if f_name == 'prepare_rule':
        prepare_rule_f = f
        break

    # Get a reference to the prefetch_rule() function.
    prefetch_rule_f = None
    for f_name, f in inspect.getmembers(module, inspect.isfunction):
      if f_name == 'prefetch_rule':
        prefetch_rule_f = f
        break

    # Get module docstring.
    doc = inspect.getdoc(module)
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
                    prepare_rule_f=prepare_rule_f,
                    prefetch_rule_f=prefetch_rule_f,
                    short_desc=short_desc,
                    long_desc=long_desc)
    return rule

  def load_rules(self, pkg):
    for name in LintRuleRepository._iter_namespace(pkg):
      try:
        if '_ext_' in name and not self.load_extended:
          continue
        rule = self.get_rule_by_module_name(name)
      except NotLintRule:
        continue

      self.register_rule(rule)

  def run_rules(self,
                context: models.Context,
                report: LintReport,
                include: Iterable[LintRulesPattern] = None,
                exclude: Iterable[LintRulesPattern] = None) -> int:

    # Make sure the rules are sorted alphabetically
    self.rules.sort(key=str)

    # Run the "prepare_rule" functions first, in a single thread.
    for rule in self.list_rules(include, exclude):
      if rule.prepare_rule_f:
        rule.prepare_rule_f(context)

    # Start multiple threads for logs fetching and prefetch functions.
    executor = get_executor()
    # Start fetching any logs queries that were defined in prepare_rule
    # functions.
    logs.execute_queries(executor)

    # Run the "prefetch_rule" functions with multiple worker threads to speed up
    # execution of the "run_rule" executions later.
    for rule in self.list_rules(include, exclude):
      if rule.prefetch_rule_f:
        rule.prefetch_rule_future = executor.submit(rule.prefetch_rule_f,
                                                    context)

    # While the prefetch_rule functions are still being executed in multiple
    # threads, start executing the rules, but block and wait in case the
    # prefetch for a specific rule is still running.
    for rule in self.list_rules(include, exclude):
      rule_report = report.rule_start(rule, context)

      try:
        if rule.prefetch_rule_future:
          if rule.prefetch_rule_future.running():
            logging.info('waiting for query results')
          rule.prefetch_rule_future.result()

        rule.run_rule_f(context, rule_report)
      except (utils.GcpApiError, googleapiclient.errors.HttpError) as err:
        if isinstance(err, googleapiclient.errors.HttpError):
          err = utils.GcpApiError(err)
        logging.warning('%s', str(err))
        report.add_skipped(rule, context, None, f'API error: {err}', None)
      except (RuntimeError, ValueError) as err:
        logging.warning('%s', str(err))
        report.add_skipped(rule, context, None, f'Error: {err}', None)
      report.rule_end(rule, context)
    return report.finish(context)

  def list_rules(
      self,
      include: Iterable[LintRulesPattern] = None,
      exclude: Iterable[LintRulesPattern] = None) -> Iterator[LintRule]:
    for rule in self.rules:
      if include:
        if not any(x.match_rule(rule) for x in include):
          continue
      if exclude:
        if any(x.match_rule(rule) for x in exclude):
          continue
      yield rule
