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
from typing import Any, Dict, List, Optional

from gcp_doctor import models
from gcp_doctor.utils import GcpApiError

MAX_WORKERS = 5


class LintRuleClass(enum.Enum):
  ERR = 'ERR'
  BP = 'BP'
  SEC = 'SEC'
  WARN = 'WARN'

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
  prefetch_rule_f: Optional[Callable] = None
  prefetch_rule_future: Optional[concurrent.futures.Future] = None

  def __hash__(self):
    return str(self.product + self.rule_class.value + self.rule_id).__hash__()

  def __str__(self):
    return self.product + '/' + self.rule_class.value + '/' + self.rule_id


class LintReport:
  """Represent a lint report, which can be terminal-based, or (in the future) JSON."""

  rules_report: Dict[LintRule, Dict[str, Any]]

  def __init__(self):
    self.rules_report = dict()

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
    # did any rule fail? Then exit with 1, otherwise 0.
    if any(r['overall_status'] == 'failed' for r in self.rules_report.values()):
      return 1
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


class LintRuleRepository:
  """Repository of Lint rule which is also used to run the rules."""
  rules: List[LintRule]

  def __init__(self):
    self.rules = []

  def register_rule(self, rule: LintRule):
    self.rules.append(rule)

  @staticmethod
  def _iter_namespace(ns_pkg):
    """Workaround for https://github.com/pyinstaller/pyinstaller/issues/1905."""
    prefix = ns_pkg.__name__ + '.'
    for p in pkgutil.iter_modules(ns_pkg.__path__, prefix):
      yield p[1]
    toc = set()
    for importer in pkgutil.iter_importers(ns_pkg.__name__.partition('.')[0]):
      if hasattr(importer, 'toc'):
        toc |= importer.toc
    for name in toc:
      if name.startswith(prefix):
        yield name

  def load_rules(self, pkg):
    for name in LintRuleRepository._iter_namespace(pkg):
      # Skip code tests
      if name.endswith('_test'):
        continue

      # Determine Lint Rule parameters based on the module name.
      m = re.search(
          r"""
           \.([^\.]+)\. # product path, e.g.: .gke.
           ([a-z]+)_    # class prefix, e.g.: 'err_'
           (\d+_\d+)    # id: 2020_001
        """, name, re.VERBOSE)
      if not m:
        logging.warning('can\'t determine rule attributes from module name: %s',
                        name)
        continue
      product, rule_class, rule_id = m.group(1, 2, 3)

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

      # Get a reference to the prefetch_rule() function.
      prefetch_rule_f = None
      for f_name, f in inspect.getmembers(module, inspect.isfunction):
        if f_name == 'prefetch_rule':
          prefetch_rule_f = f
          break

      # Get module docstring.
      doc = inspect.getdoc(module)
      if not doc:
        raise RuntimeError(
            f'module {module} doesn\'t provide a module docstring')
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
                      prefetch_rule_f=prefetch_rule_f,
                      short_desc=short_desc,
                      long_desc=long_desc)

      self.register_rule(rule)

  def run_rules(self, context: models.Context, report: LintReport) -> int:
    # Run the "prefetch_rule" functions with multiple worker threads to speed up
    # execution of the "run_rule" executions later.
    with concurrent.futures.ThreadPoolExecutor(
        max_workers=MAX_WORKERS) as prefetch_executor:
      for rule in self.rules:
        if rule.prefetch_rule_f:
          rule.prefetch_rule_future = prefetch_executor.submit(
              rule.prefetch_rule_f, context)

      self.rules.sort(key=str)
      for rule in self.rules:
        rule_report = report.rule_start(rule, context)

        if rule.prefetch_rule_future:
          if rule.prefetch_rule_future.running():
            logging.info('waiting for query results')
          rule.prefetch_rule_future.result()

        try:
          rule.run_rule_f(context, rule_report)
        except (ValueError) as e:
          report.add_skipped(rule, context, None, str(e), None)
        except (GcpApiError) as api_error:
          report.add_skipped(rule, context, None, str(api_error), None)
        report.rule_end(rule, context)
    return report.finish(context)
