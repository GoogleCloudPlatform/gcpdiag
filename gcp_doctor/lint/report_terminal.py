# Lint as: python3
"""LintReport implementation that outputs to the terminal."""

import abc
import logging
import sys

import blessings

from gcp_doctor import config, lint, models

OUTPUT_WIDTH = 68


class _LintReportTerminalLoggingHandler(logging.Handler):
  """logging.Handler implementation used when producing a lint report."""

  def __init__(self, report):
    super().__init__()
    self.report = report

  def format(self, record: logging.LogRecord):
    return record.getMessage()

  def emit(self, record):
    msg = '   ... ' + self.format(record) + ' '
    # make sure we don't go beyond the terminal width
    if self.report.term.width:
      term_overflow = len(msg) - self.report.term.width
      if term_overflow > 0:
        msg = msg[:-term_overflow]
    if record.levelno <= logging.INFO:
      self.report.terminal_update_line(msg)
    else:
      self.report.terminal_finish_line(msg)


class LintReportTerminal(lint.LintReport):
  """LintReport implementation that outputs to the terminal."""

  def __init__(self, file=sys.stdout):
    self.file = file
    if file == sys.stdout:
      self.term = blessings.Terminal()
    else:
      self.term = blessings.Terminal()

  def lint_start(self, context):
    if self.term.does_styling:
      print('gcp-doctor 🩺 ' + config.VERSION)
    else:
      print('gcp-doctor ' + config.VERSION)

    print(f'Starting lint tests ({context})...\n')

  def terminal_update_line(self, text: str):
    """Update the current line on the terminal."""
    if self.term.width:
      print(self.term.move_x(0) + self.term.clear_eol() + text,
            end='',
            flush=True,
            file=self.file)
    else:
      # If it's a stream, do not output anything, assuming that the
      # interesting output will be passed via terminal_finish_line
      pass

  def terminal_finish_line(self, text: str):
    """Write a line to the terminal, replacing any current line content, and add a line feed."""
    if self.term.width:
      self.terminal_update_line(text)
      print(file=self.file)
    else:
      print(text, file=self.file)

  def get_logging_handler(self):
    return _LintReportTerminalLoggingHandler(self)

  def test_start(self, test: lint.LintTest, context: models.Context):
    test_interface = super().test_start(test, context)
    bullet = ''
    if self.term.does_styling:
      bullet = '🔎 '
    else:
      bullet = '*  '
    self.terminal_finish_line(
        bullet +
        self.term.yellow(f'{test.product}/{test.test_class}/{test.test_id}') +
        ': ' + self.term.italic(f'{test.short_desc}'))
    return test_interface

  def test_end(self, test: lint.LintTest, context: models.Context):
    super().test_end(test, context)
    print(file=self.file)

  def add_skipped(self, test: lint.LintTest, context: models.Context,
                  resource: models.Resource, reason: str):
    self.terminal_finish_line('   - ' +
                              resource.get_short_path().ljust(OUTPUT_WIDTH) +
                              ' [SKIP]')
    self.terminal_finish_line(f'     {reason}')

  @abc.abstractmethod
  def add_ok(self, test: lint.LintTest, context: models.Context,
             resource: models.Resource):
    self.terminal_finish_line('   - ' +
                              resource.get_short_path().ljust(OUTPUT_WIDTH) +
                              ' [' + self.term.green(' OK ') + ']')

  @abc.abstractmethod
  def add_failed(self, test: lint.LintTest, context: models.Context,
                 resource: models.Resource, reason: str):
    self.terminal_finish_line('   - ' +
                              resource.get_short_path().ljust(OUTPUT_WIDTH) +
                              ' [' + self.term.red('FAIL') + ']')
    self.terminal_finish_line(f'     {reason}')
