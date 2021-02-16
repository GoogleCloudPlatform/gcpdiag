# Lint as: python3
"""LintReport implementation that outputs to the terminal."""

import abc
import logging
import os
import sys
import textwrap
from typing import Optional

import blessings

from gcp_doctor import config, lint, models

OUTPUT_WIDTH = 68


def _emoji_wrap(char):
  if os.getenv('CLOUD_SHELL'):
    # emoji not displayed as double width in Cloud Shell (bug?)
    return char + ' '
  else:
    return char


class _LintReportTerminalLoggingHandler(logging.Handler):
  """logging.Handler implementation used when producing a lint report."""

  def __init__(self, report):
    super().__init__()
    self.report = report

  def format(self, record: logging.LogRecord):
    return record.getMessage()

  def emit(self, record):
    if record.levelno == logging.INFO and self.report.log_info_for_progress_only:
      msg = '   ... ' + self.format(record) + ' '
      # make sure we don't go beyond the terminal width
      if self.report.term.width:
        term_overflow = len(msg) - self.report.term.width
        if term_overflow > 0:
          msg = msg[:-term_overflow]
      self.report.terminal_update_line(msg)
    else:
      msg = f'[{record.levelname}] ' + self.format(record) + ' '
      # workaround for bug:
      # https://github.com/googleapis/google-api-python-client/issues/1116
      if 'Invalid JSON content from response' in msg:
        return
      self.report.terminal_print_line(msg)


class LintReportTerminal(lint.LintReport):
  """LintReport implementation that outputs to the terminal."""

  def __init__(self, file=sys.stdout, log_info_for_progress_only=True):
    self.file = file
    self.line_unfinished = False
    self.log_info_for_progress_only = log_info_for_progress_only
    self.per_test_data = {}
    if file == sys.stdout:
      self.term = blessings.Terminal()
    else:
      self.term = blessings.Terminal()

  def _wrap_indent(self, text, prefix):
    width = self.term.width or 80
    if width > 80:
      width = 80
    return textwrap.indent(textwrap.fill(text, width - len(prefix)), prefix)

  def banner(self):
    if self.term.does_styling:
      print(
          self.term.bold('gcp-doctor ' + _emoji_wrap('🩺') + ' ' +
                         config.VERSION) + '\n')
    else:
      print('gcp-doctor ' + config.VERSION + '\n')

  def lint_start(self, context):
    print(f'Starting lint tests ({context})...\n')

  def terminal_update_line(self, text: str):
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

  def terminal_erase_line(self):
    """Remove the current content on the line."""
    if self.line_unfinished and self.term.width:
      print(self.term.move_x(0) + self.term.clear_eol(),
            flush=True,
            end='',
            file=self.file)
    self.line_unfinished = False

  def terminal_print_line(self, text: str = ''):
    """Write a line to the terminal, replacing any current line content, and add a line feed."""
    if self.line_unfinished and self.term.width:
      self.terminal_update_line(text)
      print(file=self.file)
    else:
      print(text, file=self.file)
    self.line_unfinished = False

  def get_logging_handler(self):
    return _LintReportTerminalLoggingHandler(self)

  def test_start(self, test: lint.LintTest, context: models.Context):
    test_interface = super().test_start(test, context)
    bullet = ''
    if self.term.does_styling:
      bullet = _emoji_wrap('🔎') + ' '
    else:
      bullet = '*  '
    self.terminal_print_line(
        bullet +
        self.term.yellow(f'{test.product}/{test.test_class}/{test.test_id}') +
        ': ' + f'{test.short_desc}')
    return test_interface

  def test_end(self, test: lint.LintTest, context: models.Context):
    super().test_end(test, context)
    self.terminal_erase_line()
    self.terminal_print_line()

    # If the test failed, add more information about the test.
    if test in self.per_test_data and self.per_test_data[test]['failed_count']:
      width = self.term.width or 80
      if width > 80:
        width = 80
      self.terminal_print_line(
          self.term.italic(self._wrap_indent(test.long_desc, '   ')))
      self.terminal_print_line()

  def add_skipped(self,
                  test: lint.LintTest,
                  context: models.Context,
                  resource: Optional[models.Resource],
                  reason: str,
                  short_info: str = None):
    if short_info:
      short_info = ' ' + short_info
    else:
      short_info = ''
    if resource:
      self.terminal_print_line('   - ' +
                               resource.get_short_path().ljust(OUTPUT_WIDTH) +
                               ' [SKIP]' + short_info)
    else:
      self.terminal_print_line('   - ' +
                               'All resources (error)'.ljust(OUTPUT_WIDTH) +
                               ' [SKIP]' + short_info)
    self.terminal_print_line(textwrap.indent(reason, '     '))

  @abc.abstractmethod
  def add_ok(self,
             test: lint.LintTest,
             context: models.Context,
             resource: models.Resource,
             short_info: str = None):
    if short_info:
      short_info = ' ' + short_info
    else:
      short_info = ''
    self.terminal_print_line('   - ' +
                             resource.get_short_path().ljust(OUTPUT_WIDTH) +
                             ' [' + self.term.green(' OK ') + ']' + short_info)

  @abc.abstractmethod
  def add_failed(self,
                 test: lint.LintTest,
                 context: models.Context,
                 resource: models.Resource,
                 reason: str,
                 short_info: str = None):
    test_data = self.per_test_data.setdefault(test, {'failed_count': 0})
    test_data['failed_count'] += 1
    if short_info:
      short_info = ' ' + short_info
    else:
      short_info = ''
    self.terminal_print_line('   - ' +
                             resource.get_short_path().ljust(OUTPUT_WIDTH) +
                             ' [' + self.term.red('FAIL') + ']' + short_info)
    self.terminal_print_line(textwrap.indent(reason, '     '))
