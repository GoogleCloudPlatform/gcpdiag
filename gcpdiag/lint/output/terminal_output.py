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
"""Output implementation that prints result in human-readable format."""

import functools
import logging
import os
import sys
import textwrap
from typing import Any, Dict, List, Optional, TextIO

from rich.console import Console
from rich.markup import escape

from gcpdiag import config, lint, models
from gcpdiag.lint.output import base_output

OUTPUT_WIDTH = 68


def is_cloud_shell():
  return os.getenv('CLOUD_SHELL')


def emoji_wrap(char):
  if is_cloud_shell():
    # emoji not displayed as double width in Cloud Shell (bug?)
    return char + ' '
  else:
    return char


class OutputOrderer:
  """Helper to maintain sorting order of the rules"""

  _result_handler: 'lint.LintResultsHandler'
  _output_order: List[str]
  _next_rule_idx: int
  _rule_reports_ready: Dict[str, 'lint.LintReportRuleInterface']

  def __init__(self, result_handler: 'lint.LintResultsHandler', output_order: List[str]) -> None:
    self._result_handler = result_handler
    self._output_order = output_order
    self._next_rule_idx = 0
    self._rule_reports_ready = {}

  def process_rule_report(self, rule_report: Any) -> None:
    rule_id = str(rule_report.rule)
    self._rule_reports_ready[rule_id] = rule_report
    self._output_ready()

  def _output_ready(self) -> None:
    while self._has_more_work and self._is_next_rule_ready:
      rule_report = self._rule_reports_ready[self._next_rule_id]
      self._result_handler.process_rule_report(rule_report)
      self._next_rule_idx += 1

  @property
  def _has_more_work(self) -> bool:
    return self._next_rule_idx < len(self._output_order)

  @property
  def _is_next_rule_ready(self) -> bool:
    return self._next_rule_id in self._rule_reports_ready

  @property
  def _next_rule_id(self) -> str:
    return self._output_order[self._next_rule_idx]


class TerminalOutput(base_output.BaseOutput):
  """Output implementation that prints result in human-readable format."""

  _output_order: Optional[List[str]]
  line_unfinished: bool
  console: Console

  def __init__(
    self,
    file: Optional[TextIO] = None,
    log_info_for_progress_only: bool = True,
    show_ok: bool = True,
    show_skipped: bool = False,
    output_order: Optional[List[str]] = None,
  ):
    super().__init__(file, log_info_for_progress_only, show_ok, show_skipped)
    self._output_order = output_order
    self.line_unfinished = False
    self.file = file or sys.stdout
    self.console = Console(file=self.file, highlight=False, soft_wrap=True)

  @functools.cached_property
  def result_handler(self) -> 'lint.LintResultsHandler':
    default_handler = self
    if self._output_order is None:
      return default_handler
    else:
      return OutputOrderer(result_handler=default_handler, output_order=self._output_order)

  def process_rule_report(self, rule_report: 'lint.LintReportRuleInterface') -> None:
    if not self._should_rule_be_skipped(rule_report):
      with self.lock:
        self._print_rule_report(rule_report)

  def _print_rule_report(self, rule_report: 'lint.LintReportRuleInterface') -> None:
    self._print_rule_header(rule=rule_report.rule)
    for check_result in rule_report.results:
      self._handle_rule_report_result(check_result)
    if rule_report.overall_status == 'failed':
      self._print_long_desc(rule=rule_report.rule)
    self.terminal_print_line()

  def _handle_rule_report_result(self, check_result: 'lint.LintRuleResult') -> None:
    if check_result.status == 'failed':
      self._print_failed(
        resource=check_result.resource,
        reason=check_result.reason,
        short_info=check_result.short_info,
      )
    elif check_result.status == 'skipped':
      self._print_skipped(
        resource=check_result.resource,
        reason=check_result.reason,
        short_info=check_result.short_info,
      )
    elif check_result.status == 'ok':
      self._print_ok(resource=check_result.resource, short_info=check_result.short_info)
    else:
      raise RuntimeError('Unknown rule report status')

  def _wrap_indent(self, text: str, prefix: str) -> str:
    width = self.console.width if self.console.is_terminal else 80
    width = min(width, 80)
    return textwrap.indent(textwrap.fill(text, width - len(prefix)), prefix)

  def _italic(self, text: str) -> str:
    return f'[italic]{escape(text)}[/italic]'

  def terminal_update_line(self, text: str) -> None:
    """Update the current line on the terminal."""
    if self.console.is_terminal:
      self.file.write('\r\033[K' + text)
      self.file.flush()
      self.line_unfinished = True
    else:
      # If it's a stream, do not output anything, assuming that the
      # interesting output will be passed via terminal_print_line
      pass

  def terminal_erase_line(self) -> None:
    """Remove the current content on the line."""
    if self.line_unfinished and self.console.is_terminal:
      self.file.write('\r\033[K')
      self.file.flush()
    self.line_unfinished = False

  def terminal_print_line(self, text: str = '') -> None:
    """Write a line to the terminal, replacing any current line content, and add a line feed."""
    text = text.expandtabs()
    if self.line_unfinished and self.console.is_terminal:
      self.file.write('\r\033[K')
      self.file.flush()
      self.console.print(text)
    else:
      self.console.print(text)
    # flush the output, so that we can more easily grep, tee, etc.
    self.file.flush()
    self.line_unfinished = False

  def display_banner(self) -> None:
    self.console.print(f'gcpdiag {emoji_wrap("🩺")} {config.VERSION}\n', style='bold')

  def _print_rule_header(self, rule: 'lint.LintRule') -> None:
    bullet = ''
    if self.console.is_terminal:
      bullet = emoji_wrap('🔎') + ' '
    else:
      bullet = '*  '
    self.terminal_print_line(
      bullet + f'[yellow]{escape(str(rule.product))}/{escape(str(rule.rule_class))}/'
      f'{escape(str(rule.rule_id))}[/yellow]: ' + escape(rule.short_desc)
    )

  def _print_long_desc(self, rule: 'lint.LintRule') -> None:
    self.terminal_print_line()
    long_desc = rule.long_desc or ''
    self.terminal_print_line(self._italic(self._wrap_indent(long_desc, '   ')))
    self.terminal_print_line()
    self.terminal_print_line('   ' + escape(rule.doc_url))

  def _print_skipped(
    self, resource: Optional[models.Resource], reason: Optional[str], short_info: Optional[str]
  ) -> None:
    if not self.show_skipped:
      return
    if short_info:
      short_info = ' ' + escape(short_info)
    else:
      short_info = ''
    reason = reason or ''
    if resource:
      self.terminal_print_line(
        '   - ' + escape(resource.full_path.ljust(OUTPUT_WIDTH)) + ' [SKIP]' + short_info
      )
      self.terminal_print_line(textwrap.indent(escape(reason), '     '))
    else:
      self.terminal_print_line(
        '   ' + escape(('(' + reason + ')').ljust(OUTPUT_WIDTH + 2)) + ' [SKIP]' + short_info
      )

  def _print_ok(self, resource: Optional[models.Resource], short_info: Optional[str]) -> None:
    if not self.show_ok:
      return
    if short_info:
      short_info = ' ' + escape(str(short_info))
    else:
      short_info = ''
    full_path = (
      resource.full_path if resource is not None and resource.full_path is not None else ''
    )
    self.terminal_print_line(
      '   - '
      + escape(full_path.ljust(OUTPUT_WIDTH))
      + ' ['
      + '[green] OK [/green]'
      + ']'
      + short_info
    )

  def _print_failed(
    self, resource: Optional[models.Resource], reason: Optional[str], short_info: Optional[str]
  ) -> None:
    if short_info:
      short_info = ' ' + escape(short_info)
    else:
      short_info = ''
    full_path = (
      resource.full_path if resource is not None and resource.full_path is not None else ''
    )
    self.terminal_print_line(
      '   - ' + escape(full_path.ljust(OUTPUT_WIDTH)) + ' [' + '[red]FAIL[/red]' + ']' + short_info
    )
    if reason:
      self.terminal_print_line(textwrap.indent(escape(reason), '     '))

  def get_logging_handler(self) -> logging.Handler:
    return _LoggingHandler(self)


class _LoggingHandler(logging.Handler):
  """logging.Handler implementation used when producing a lint report."""

  output: TerminalOutput

  def __init__(self, output: TerminalOutput) -> None:
    super().__init__()
    self.output = output

  def format(self, record: logging.LogRecord) -> str:
    return record.getMessage()

  def emit(self, record: logging.LogRecord) -> None:
    if record.levelno == logging.INFO and self.output.log_info_for_progress_only:
      msg = '   ... ' + self.format(record)
      # make sure we don't go beyond the terminal width
      if self.output.console.is_terminal:
        term_overflow = len(msg) - self.output.console.width
        if term_overflow > 0:
          msg = msg[:-term_overflow]
      with self.output.lock:
        self.output.terminal_update_line(msg)
    else:
      msg = f'[{record.levelname}] ' + self.format(record) + ' '
      # workaround for bug:
      # https://github.com/googleapis/google-api-python-client/issues/1116
      if 'Invalid JSON content from response' in msg:
        return
      with self.output.lock:
        self.output.terminal_print_line(escape(msg))
