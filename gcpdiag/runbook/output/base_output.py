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
""" Base class for different output implementations """
import logging
import sys
from typing import Any, Optional

from gcpdiag import models


class BaseOutput:
  """ Base class for different output implementations """

  def print_ok(self, resource: models.Resource, reason: str = '') -> None:
    pass

  def print_skipped(self,
                    resource: Optional[models.Resource],
                    reason: str,
                    remediation: str = None) -> None:
    pass

  def print_failed(self, resource: models.Resource, reason: str,
                   remediation: str) -> None:
    pass

  def print_uncertain(self,
                      resource: models.Resource,
                      reason: str,
                      remediation: str = None) -> None:
    pass

  def prompt(self,
             message: str,
             kind: str = '',
             options: dict = None,
             choice_msg: str = '',
             non_interactive: bool = None) -> Any:
    pass

  def info(self, message: str, step_type='INFO'):
    pass

  def display_runbook_description(self, tree) -> None:
    pass

  def get_logging_handler(self) -> logging.Handler:
    return _LoggingHandler()


class _LoggingHandler(logging.Handler):
  """Basic Logging Hangler"""

  def __init__(self, stream_config=None):
    super().__init__()
    self.stream_config = stream_config or {
        logging.DEBUG: sys.stdout,
        logging.INFO: sys.stdout,
        logging.WARNING: sys.stderr,
        logging.ERROR: sys.stderr,
        logging.CRITICAL: sys.stderr
    }

  def emit(self, record):
    record.msg = f'[{record.levelname}] {record.msg}'
    stream = self.stream_config.get(record.levelno, sys.stderr)
    stream.flush()
