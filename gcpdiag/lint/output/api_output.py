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
"""API class for api output implementations """
import logging
import sys

from gcpdiag import lint
from gcpdiag.lint.output import base_output


class APIOutput(base_output.BaseOutput):
  """API output implementation."""

  @property
  def result_handler(self) -> 'lint.LintResultsHandler':
    return self

  def process_rule_report(self,
                          rule_report: lint.LintReportRuleInterface) -> None:
    pass

  def get_logging_handler(self) -> logging.Handler:
    stream_handler = logging.StreamHandler(stream=sys.stdout)
    formatter = logging.Formatter('%(levelname)-6s: %(message)s')
    stream_handler.setFormatter(formatter)
    return stream_handler
