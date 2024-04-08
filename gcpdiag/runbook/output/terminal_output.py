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
""" Output implementation that prints result in human-readable format. """

import logging
import os
import sys
import textwrap
import threading
from typing import Optional, TextIO

import blessings

# pylint: disable=unused-import (lint is used in type hints)
from gcpdiag import config, models, runbook
from gcpdiag.runbook import constants, report
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
  """ Output implementation that prints result in human-readable format. """
  file: TextIO
  show_ok: bool
  show_skipped: bool
  log_info_for_progress_only: bool
  lock: threading.Lock
  line_unfinished: bool
  term: blessings.Terminal

  def __init__(self,
               file: TextIO = sys.stdout,
               log_info_for_progress_only: bool = True,
               show_ok: bool = True,
               show_skipped: bool = True):
    self.file = file
    self.show_ok = show_ok
    self.show_skipped = show_skipped
    self.log_info_for_progress_only = log_info_for_progress_only
    self.lock = threading.Lock()
    self.line_unfinished = False
    self.term = blessings.Terminal()

  def display_banner(self) -> None:
    if self.term.does_styling:
      print(self.term.bold(f"gcpdiag {emoji_wrap('🩺')} {config.VERSION}\n"))
    else:
      print(f'gcpdiag {config.VERSION}\n', file=sys.stderr)

  def display_header(self, context: models.Context) -> None:
    print(f'Starting runbook inspection [Alpha Release]\n{context}\n',
          file=sys.stderr)

  def display_runbook_description(self, tree):
    self.terminal_print_line(f'{self.term.yellow(tree.name)}: {tree.__doc__}')

  def display_footer(self, result: 'report.ReportManager') -> None:
    totals = result.get_totals_by_status()
    state_strs = [
        f'{totals.get(state, 0)} {state}'
        for state in ['skipped', 'ok', 'failed', 'uncertain']
    ]
    print(f"Rules summary: {', '.join(state_strs)}", file=sys.stderr)

  def get_logging_handler(self) -> logging.Handler:
    return _LoggingHandler(self)

  def print_line(self, text: str = '') -> None:
    """Write a line to the desired output provided as self.file."""
    print(text, file=self.file, flush=True)

  def _wrap_indent(self, text: str, prefix: str) -> str:
    width = self.term.width or 80
    width = min(width, 80)
    return textwrap.indent(textwrap.fill(text, width - len(prefix)), prefix)

  def _italic(self, text: str) -> str:
    if is_cloud_shell():
      # TODO(b/201958597): Cloud Shell with tmux doesn't format italic properly at the moment
      return text
    else:
      return self.term.italic(text)

  def terminal_update_line(self, text: str) -> None:
    """Update the current line on the terminal."""
    if self.term.width:
      print(self.term.move_x(0) + self.term.clear_eol() + text,
            end='',
            flush=True,
            file=self.file)
      self.line_unfinished = True
    else:
      # If it's a stream, do not output anything, assuming that the
      # interesting output will be passed via terminal_print_line
      pass

  def terminal_erase_line(self) -> None:
    """Remove the current content on the line."""
    if self.line_unfinished and self.term.width:
      print(self.term.move_x(0) + self.term.clear_eol(),
            flush=True,
            end='',
            file=self.file)
    self.line_unfinished = False

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

  def _print_rule_header(self, rule: 'runbook.DiagnosticTree') -> None:
    bullet = ''
    if self.term.does_styling:
      bullet = emoji_wrap('🔎') + ' '
    else:
      bullet = '*  '
    self.terminal_print_line(bullet + self.term.yellow(rule.name))

  def _print_long_desc(self, rule: 'runbook.DiagnosticTree') -> None:
    self.terminal_print_line()
    self.terminal_print_line(
        self._italic(self._wrap_indent(rule.__doc__ or '', '   ')))
    self.terminal_print_line()
    self.terminal_print_line('   ' + rule.doc_url)

  def print_skipped(self,
                    resource: Optional[models.Resource],
                    reason: str,
                    remediation: str = None) -> None:


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

  def print_ok(self, resource: models.Resource, reason: str = '') -> None:
    if not self.show_ok:
      return
    short_path = resource.short_path if resource is not None \
                 and resource.short_path is not None else ''
    self.terminal_print_line()
    self.terminal_print_line('   - ' + short_path.ljust(OUTPUT_WIDTH) + ' [' +
                             self.term.green('OK') + ']')
    if reason:
      self.terminal_print_line('     [' + self.term.green('REASON') + ']')
      self.terminal_print_line(textwrap.indent(reason, '     '))

  def print_failed(self, resource: models.Resource, reason: str,
                   remediation: str) -> None:
    """Output test result and registers the result to be used in
    the runbook report.

    The failure assigned a human task unless program is running
    autonomously
    """


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

  def print_uncertain(self,
                      resource: models.Resource,
                      reason: str,
                      remediation: str = None) -> None:

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

  def info(self, message: str, step_type='INFO'):
    """
    For informational update and getting a response from user
    """
    self.terminal_print_line(text='' + '[' + self.term.green(step_type) +
                             ']: ' + f'{message}')

  def prompt(self,
             message: str,
             step: str = '',
             options: dict = None,
             choice_msg: str = 'Choose an option: ',
             non_interactive: bool = None):
    """
    For informational update and getting a response from user
    """
    non_interactive = non_interactive or config.get(INTERACTIVE_MODE)
    if non_interactive:
      return
    self.terminal_print_line(text='' + '[' + self.term.green(step) + ']: ' +
                             f'{message}')

    self.default_answer = False
    self.answer = None
    options_text = '\n'
    try:
      if step in constants.HUMAN_TASK and not options:
        for option, description in constants.HUMAN_TASK_OPTIONS.items():
          options_text += '[' + self.term.green(
              f'{option}') + ']' + f' - {description}\n'
      if step in constants.CONFIRMATION and not options:
        for option, description in constants.CONFIRMATION_OPTIONS.items():
          options_text += '[' + self.term.green(
              f'{option}') + ']' + f' - {description}\n'
      if (step in constants.CONFIRMATION or step in constants.HUMAN_TASK) \
        and options:
        for option, description in options.items():
          options_text += '[' + self.term.green(
              f'{option}') + ']' + f' - {description}\n'

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
    elif self.answer.strip().lower() not in [
        's', 'stop', 'c', 'continue', 'r', 'retest'
    ]:
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
      if self.output.term.width:
        term_overflow = len(msg) - self.output.term.width
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
        self.output.terminal_print_line(msg)
