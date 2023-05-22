""" Base class for different output implementations """
import logging
import sys
import threading
from typing import TextIO

# pylint: disable=unused-import (lint is used in type annotations)
from gcpdiag import config, lint, models


class BaseOutput:
  """ Base class for different output implementations """
  file: TextIO
  show_ok: bool
  show_skipped: bool
  log_info_for_progress_only: bool
  lock: threading.Lock

  def __init__(self,
               file: TextIO = sys.stdout,
               log_info_for_progress_only: bool = True,
               show_ok: bool = True,
               show_skipped: bool = False) -> None:
    self.file = file
    self.show_ok = show_ok
    self.show_skipped = show_skipped
    self.log_info_for_progress_only = log_info_for_progress_only
    self.lock = threading.Lock()

  def display_banner(self) -> None:
    print(f'gcpdiag {config.VERSION}\n', file=sys.stderr)

  def display_header(self, context: models.Context) -> None:
    print(f'Starting lint inspection ({context})...\n', file=sys.stderr)

  def display_footer(self, result: 'lint.LintResults') -> None:
    totals = result.get_totals_by_status()
    state_strs = [
        f'{totals.get(state, 0)} {state}'
        for state in ['skipped', 'ok', 'failed']
    ]
    print(f"Rules summary: {', '.join(state_strs)}", file=sys.stderr)

  def get_logging_handler(self) -> logging.Handler:
    return _LoggingHandler(self)

  def print_line(self, text: str = '') -> None:
    """Write a line to the desired output provided as self.file."""
    print(text, file=self.file, flush=True)

  def _should_result_be_skipped(self, result: 'lint.LintRuleResult') -> bool:
    skipped = result.status == 'skipped' and not self.show_skipped
    ok = result.status == 'ok' and not self.show_ok
    return skipped or ok

  def _should_rule_be_skipped(
      self, rule_report: 'lint.LintReportRuleInterface') -> bool:
    skipped = rule_report.overall_status == 'skipped' and not self.show_skipped
    ok = rule_report.overall_status == 'ok' and not self.show_ok
    return skipped or ok


class _LoggingHandler(logging.Handler):
  """logging.Handler implementation used when producing a lint report."""
  output: BaseOutput

  def __init__(self, output: BaseOutput):
    super().__init__()
    self.output = output

  def format(self, record: logging.LogRecord) -> str:
    return record.getMessage()

  def emit(self, record: logging.LogRecord) -> None:
    if record.levelno == logging.INFO:
      # Do not output anything, assuming that the
      # interesting output will be passed via print_line
      return
    else:
      msg = f'[{record.levelname}] ' + self.format(record) + ' '
      # workaround for bug:
      # https://github.com/googleapis/google-api-python-client/issues/1116
      if 'Invalid JSON content from response' in msg:
        return
    with self.output.lock:
      sys.stdout.flush()
      print(msg, file=sys.stderr)
