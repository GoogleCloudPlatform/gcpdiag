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
"""Output implementation that prints result in human-readable format."""

import logging
import os
import sys
import textwrap
import threading
from typing import Any, Optional, TextIO

from rich.console import Console
from rich.markup import escape

from gcpdiag import config, models, runbook
from gcpdiag.runbook import constants
from gcpdiag.runbook.flags import INTERACTIVE_MODE
from gcpdiag.runbook.output.base_output import BaseOutput

OUTPUT_WIDTH = 68


def is_cloud_shell():
  return os.getenv('CLOUD_SHELL')


def emoji_wrap(char):
  if is_cloud_shell():
    # emoji not displayed as double width in Cloud Shell (bug?)
    return char + ' '
  else:
    return char


class TerminalOutput(BaseOutput):
  """Output implementation that prints result in human-readable format."""

  file: TextIO
  show_ok: bool
  show_skipped: bool
  log_info_for_progress_only: bool
  lock: threading.Lock
  line_unfinished: bool
  console: Console

  def __init__(
    self,
    file: Optional[TextIO] = None,
    log_info_for_progress_only: bool = True,
    show_ok: bool = True,
    show_skipped: bool = True,
  ):
    self.file = file or sys.stdout
    self.console = Console(file=self.file, highlight=False, soft_wrap=True)
    self.show_ok = show_ok
    self.show_skipped = show_skipped
    self.log_info_for_progress_only = log_info_for_progress_only
    self.lock = threading.Lock()
    self.line_unfinished = False

  def display_banner(self) -> None:
    self.console.print(f'gcpdiag {emoji_wrap("🩺")} {config.VERSION}\n', style='bold')

  def display_header(self) -> None:
    self.console.print('Starting runbook inspection [Alpha Release]\n')

  def display_runbook_description(self, tree):
    self.terminal_print_line(f'[yellow]{escape(tree.name)}[/yellow]: {escape(tree.__doc__)}')

  def display_footer(self, result) -> None:
    totals = result.get_totals_by_status()
    state_strs = [
      f'{totals.get(state, 0)} {state}' for state in ['skipped', 'ok', 'failed', 'uncertain']
    ]
    self.console.print(f'Rules summary: {", ".join(state_strs)}')

  def get_logging_handler(self) -> logging.Handler:
    return _LoggingHandler(self)

  def print_line(self, text: str = '') -> None:
    """Write a line to the desired output provided as self.file."""
    print(text, file=self.file, flush=True)

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

  def _print_rule_header(self, rule: 'runbook.DiagnosticTree') -> None:
    bullet = ''
    if self.console.is_terminal:
      bullet = emoji_wrap('🔎') + ' '
    else:
      bullet = '*  '
    self.terminal_print_line(bullet + f'[yellow]{escape(rule.name)}[/yellow]')

  def _print_long_desc(self, rule: 'runbook.DiagnosticTree') -> None:
    self.terminal_print_line()
    self.terminal_print_line(self._italic(self._wrap_indent(rule.__doc__ or '', '   ')))
    self.terminal_print_line()
    self.terminal_print_line('   ' + escape(rule.doc_url))

  def print_skipped(
    self, resource: Optional[models.Resource], reason: str, remediation: str = None
  ) -> None:
    self.terminal_print_line()
    short_path = (
      resource.short_path if resource is not None and resource.short_path is not None else ''
    )
    self.terminal_print_line(
      '   - ' + escape(short_path.ljust(OUTPUT_WIDTH)) + ' [' + '[yellow]SKIP[/yellow]' + ']'
    )
    if reason:
      self.terminal_print_line('     [' + '[green]REASON[/green]' + ']')
      self.terminal_print_line(textwrap.indent(escape(reason), '     '))

    if remediation:
      self.terminal_print_line('     [' + '[green]REMEDIATION[/green]' + ']')
      self.terminal_print_line(textwrap.indent(escape(remediation), '     '))

  def print_ok(self, resource: Optional[models.Resource], reason: str = '') -> None:
    if not self.show_ok:
      return
    self.terminal_print_line()
    short_path = (
      resource.short_path if resource is not None and resource.short_path is not None else ''
    )
    self.terminal_print_line(
      '   - ' + escape(short_path.ljust(OUTPUT_WIDTH)) + ' [' + '[green]OK[/green]' + ']'
    )
    if reason:
      self.terminal_print_line('     [' + '[green]REASON[/green]' + ']')
      self.terminal_print_line(textwrap.indent(escape(reason), '     '))

  def print_failed(
    self, resource: Optional[models.Resource], reason: str, remediation: str
  ) -> None:
    """Output test result and registers the result to be used in
    the runbook report.

    The failure assigned a human task unless program is running
    autonomously
    """
    self.terminal_print_line()
    short_path = (
      resource.short_path if resource is not None and resource.short_path is not None else ''
    )
    self.terminal_print_line(
      '   - ' + escape(short_path.ljust(OUTPUT_WIDTH)) + ' [' + '[red]FAIL[/red]' + ']'
    )
    if reason:
      self.terminal_print_line('     [' + '[green]REASON[/green]' + ']')
      self.terminal_print_line(textwrap.indent(escape(reason), '     '))

    if remediation:
      self.terminal_print_line('     [' + '[green]REMEDIATION[/green]' + ']')
      self.terminal_print_line(textwrap.indent(escape(remediation), '     '))

  def print_uncertain(
    self, resource: Optional[models.Resource], reason: str, remediation: str = None
  ) -> None:
    self.terminal_print_line()
    short_path = (
      resource.short_path if resource is not None and resource.short_path is not None else ''
    )
    self.terminal_print_line(
      '   - ' + escape(short_path.ljust(OUTPUT_WIDTH)) + ' [' + '[yellow]UNCERTAIN[/yellow]' + ']'
    )
    if reason:
      self.terminal_print_line('     [' + '[green]REASON[/green]' + ']')
      self.terminal_print_line(textwrap.indent(escape(reason), '     '))

    if remediation:
      self.terminal_print_line('     [' + '[green]REMEDIATION[/green]' + ']')
      self.terminal_print_line(textwrap.indent(escape(remediation), '     '))

  def info(self, message: str, step_type='INFO'):
    """
    For informational update and getting a response from user
    """
    self.terminal_print_line(
      text='' + '[' + f'[green]{escape(step_type)}[/green]' + ']: ' + f'{escape(message)}'
    )

  def prompt(
    self,
    message: str,
    kind: str = '',
    options: dict = None,
    choice_msg: str = 'Choose an option: ',
    non_interactive: bool = None,
  ) -> Any:
    """
    For informational update and getting a response from user
    """
    non_interactive = non_interactive or config.get(INTERACTIVE_MODE)
    if non_interactive:
      return
    self.terminal_print_line(
      text='' + '[' + f'[green]{escape(kind)}[/green]' + ']: ' + f'{escape(message)}'
    )

    self.default_answer = False
    self.answer = None
    options_text = '\n'
    try:
      if kind in constants.HUMAN_TASK and not options:
        for option, description in constants.HUMAN_TASK_OPTIONS.items():
          options_text += (
            '[' + f'[green]{escape(str(option))}[/green]' + ']' + f' - {escape(description)}\n'
          )
      if kind in constants.CONFIRMATION and not options:
        for option, description in constants.CONFIRMATION_OPTIONS.items():
          options_text += (
            '[' + f'[green]{escape(str(option))}[/green]' + ']' + f' - {escape(description)}\n'
          )
      if (kind in constants.CONFIRMATION or kind in constants.HUMAN_TASK) and options:
        for option, description in options.items():
          options_text += (
            '[' + f'[green]{escape(str(option))}[/green]' + ']' + f' - {escape(description)}\n'
          )

      if options_text:
        self.terminal_print_line(text=textwrap.indent(options_text, '     '))
        self.answer = input(textwrap.indent(choice_msg, '     '))
    except EOFError:
      return self.answer
    # We explicitly want to
    # distinguish between empty string and None.
    if self.answer == '':
      # User just hit enter, return default.
      return self.default_answer
    elif self.answer is None:
      return self.answer
    elif self.answer.strip().lower() in ['s', 'stop']:
      return constants.STOP
    elif self.answer.strip().lower() in ['c', 'continue']:
      return constants.CONTINUE
    elif self.answer.strip().lower() in ['u', 'uncertain']:
      return constants.UNCERTAIN
    elif self.answer.strip().lower() in ['r', 'retest']:
      return constants.RETEST
    elif self.answer.strip().lower() in ['y', 'yes']:
      return constants.YES
    elif self.answer.strip().lower() in ['n', 'no']:
      return constants.NO
    elif self.answer.strip().lower() not in ['s', 'stop', 'c', 'continue', 'r', 'retest']:
      return self.answer.strip()
    return


class _LoggingHandler(logging.Handler):
  """logging.Handler implementation used when producing a runbook report."""

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
