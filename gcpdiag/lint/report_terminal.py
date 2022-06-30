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
"""LintReport implementation that outputs to the terminal."""

import logging
import os
import sys
import textwrap
from typing import Optional

import blessings

from gcpdiag import config, lint, models

OUTPUT_WIDTH = 68


def is_cloud_shell():
  return os.getenv('CLOUD_SHELL')


def emoji_wrap(char):
  if is_cloud_shell():
    # emoji not displayed as double width in Cloud Shell (bug?)
    return char + ' '
  else:
    return char


class LintReportTerminal(lint.LintReport):
  """LintReport implementation that outputs to the terminal."""

  def __init__(self,
               file=sys.stdout,
               log_info_for_progress_only=True,
               show_ok=True,
               show_skipped=False):
    super().__init__(file, log_info_for_progress_only, show_ok, show_skipped)
    self.line_unfinished = False
    self.per_rule_data = {}
    self.term = blessings.Terminal()

  def _wrap_indent(self, text, prefix):
    width = self.term.width or 80
    width = min(width, 80)
    return textwrap.indent(textwrap.fill(text, width - len(prefix)), prefix)

  def _italic(self, text):
    if is_cloud_shell():
      # TODO(b/201958597): Cloud Shell with tmux doesn't format italic properly at the moment
      return text
    else:
      return self.term.italic(text)

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
      # flush the output, so that we can more easily grep, tee, etc.
      sys.stdout.flush()
    self.line_unfinished = False

  def banner(self):
    if self.term.does_styling:
      print(self.term.bold(f"gcpdiag {emoji_wrap('🩺')} {config.VERSION}\n"))
    else:
      print(f'gcpdiag {config.VERSION}\n', file=sys.stderr)

  def rule_start(self, rule: lint.LintRule, context: models.Context):
    rule_interface = super().rule_start(rule, context)
    bullet = ''
    if self.term.does_styling:
      bullet = emoji_wrap('🔎') + ' '
    else:
      bullet = '*  '
    self.terminal_print_line(
        bullet +
        self.term.yellow(f'{rule.product}/{rule.rule_class}/{rule.rule_id}') +
        ': ' + f'{rule.short_desc}')
    return rule_interface

  def rule_end(self, rule: lint.LintRule, context: models.Context):
    self.terminal_erase_line()
    if self.rule_has_results:
      self.terminal_print_line()
    else:
      # if we printed nothing about this rule (probably because
      # skipped, and --hide-skipped active), then also don't
      # print the rule line -> overwrite it with the next.
      print(self.term.move_up + self.term.clear_eol(),
            flush=True,
            end='',
            file=self.file)

    # If the rule failed, add more information about the rule.
    if rule in self.per_rule_data and self.per_rule_data[rule]['failed_count']:
      width = self.term.width or 80
      width = min(width, 80)
      self.terminal_print_line(
          self._italic(self._wrap_indent(rule.long_desc, '   ')))
      self.terminal_print_line()
      self.terminal_print_line('   ' + rule.doc_url)
      self.terminal_print_line()

  def add_skipped(self, rule: lint.LintRule, context: models.Context,
                  resource: Optional[models.Resource], reason: str,
                  short_info: Optional[str]):
    super().add_skipped(rule, context, resource, reason, short_info)
    if not self.show_skipped:
      return
    self.rule_has_results = True
    if short_info:
      short_info = ' ' + short_info
    else:
      short_info = ''
    if resource:
      self.terminal_print_line('   - ' +
                               resource.short_path.ljust(OUTPUT_WIDTH) +
                               ' [SKIP]' + short_info)
      self.terminal_print_line(textwrap.indent(reason, '     '))
    else:
      self.terminal_print_line('   ' +
                               ('(' + reason + ')').ljust(OUTPUT_WIDTH + 2) +
                               ' [SKIP]' + short_info)

  def add_ok(self, rule: lint.LintRule, context: models.Context,
             resource: models.Resource, short_info: Optional[str]):
    super().add_ok(rule, context, resource, short_info)
    if not self.show_ok:
      return
    self.rule_has_results = True
    if short_info:
      short_info = ' ' + str(short_info)
    else:
      short_info = ''
    self.terminal_print_line('   - ' + resource.short_path.ljust(OUTPUT_WIDTH) +
                             ' [' + self.term.green(' OK ') + ']' + short_info)

  def add_failed(self, rule: lint.LintRule, context: models.Context,
                 resource: models.Resource, reason: Optional[str],
                 short_info: Optional[str]):
    super().add_failed(rule, context, resource, reason, short_info)
    self.rule_has_results = True
    rule_data = self.per_rule_data.setdefault(rule, {'failed_count': 0})
    rule_data['failed_count'] += 1
    if short_info:
      short_info = ' ' + short_info
    else:
      short_info = ''
    self.terminal_print_line('   - ' + resource.short_path.ljust(OUTPUT_WIDTH) +
                             ' [' + self.term.red('FAIL') + ']' + short_info)
    if reason:
      self.terminal_print_line(textwrap.indent(reason, '     '))

  def get_logging_handler(self):
    return _LintReportTerminalLoggingHandler(self)


class _LintReportTerminalLoggingHandler(logging.Handler):
  """logging.Handler implementation used when producing a lint report."""

  def __init__(self, report):
    super().__init__()
    self.report = report

  def format(self, record: logging.LogRecord):
    return record.getMessage()

  def emit(self, record):
    if record.levelno == logging.INFO and self.report.log_info_for_progress_only:
      msg = '   ... ' + self.format(record)
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
