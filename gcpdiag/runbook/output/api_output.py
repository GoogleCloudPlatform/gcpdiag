# Copyright 2024 Google LLC
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
"""API class for api output implementations"""

import logging
import sys

from gcpdiag.runbook.output.base_output import BaseOutput


class ApiOutput(BaseOutput):
  """API output implementation."""

  def __init__(self, execution_id=None):
    super().__init__()
    self.execution_id = execution_id

  def get_logging_handler(self) -> logging.Handler:
    stream_handler = logging.StreamHandler(stream=sys.stdout)
    formatter = logging.Formatter(self._get_log_format())
    stream_handler.setFormatter(formatter)
    return stream_handler

  def _get_log_format(self):
    log_format = '[%(levelname)-6s] '
    if self.execution_id:
      log_format += f'[EID: {self.execution_id}] '
    log_format += '%(message)s'
    return log_format
