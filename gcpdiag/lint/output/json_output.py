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
""" Output implementation that prints result in JSON format. """

import json
from typing import Optional

from gcpdiag import lint, models
from gcpdiag.lint.output import base_output


class JSONOutput(base_output.BaseOutput):
  """ Output implementation that prints result in JSON format. """

  _printed_first_result = False

  def display_header(self, context: models.Context) -> None:
    super().display_header(context)
    # group output as list - start
    self.print_line('[')

  def display_footer(self, result: lint.LintResults) -> None:
    # group output as list - end
    self.print_line(']')
    # add extra line
    self.print_line()
    return super().display_footer(result)

  @property
  def result_handler(self) -> 'lint.LintResultsHandler':
    return self

  def process_rule_report(self,
                          rule_report: lint.LintReportRuleInterface) -> None:
    with self.lock:
      self._print_rule_report(rule_report)

  def _print_rule_report(self,
                         rule_report: lint.LintReportRuleInterface) -> None:
    for result in rule_report.results:
      if not self._should_result_be_skipped(result):
        self._add_result(rule=rule_report.rule,
                         resource=result.resource,
                         status=result.status,
                         reason=result.reason,
                         short_info=result.short_info)

  def _add_result(self,
                  rule: lint.LintRule,
                  resource: Optional[models.Resource],
                  status: str,
                  short_info: Optional[str] = None,
                  reason: Optional[str] = None) -> None:
    self.rule_has_results = True
    rule_id = f'{rule.product}/{rule.rule_class}/{rule.rule_id}'
    if reason:
      message = '' + reason
    elif short_info:
      message = '' + short_info
    else:
      message = '-'
    if self._printed_first_result:
      self.print_line(',')
    else:
      self._printed_first_result = True
    self.print_line(
        json.dumps(
            {
                'rule': rule_id,
                'resource': resource.full_path if resource else '-',
                'status': status,
                'message': message,
                'doc_url': rule.doc_url
            },
            ensure_ascii=False,
            indent=2))
