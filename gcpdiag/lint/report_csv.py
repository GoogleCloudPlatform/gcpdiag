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
"""LintReport implementation that outputs to the csv."""

import csv
import sys
from typing import Optional

from gcpdiag import lint, models


class LintReportCsv(lint.LintReport):
  """LintReport implementation that outputs to the terminal."""

  columns = ['rule', 'resource', 'status', 'message', 'doc_url']

  def __init__(self,
               file=sys.stdout,
               log_info_for_progress_only=True,
               show_ok=True,
               show_skipped=False):
    super().__init__(file, log_info_for_progress_only, show_ok, show_skipped)
    self.writer = csv.DictWriter(sys.stdout, fieldnames=self.columns)

  def rule_start(self, rule: lint.LintRule, context: models.Context):
    rule_interface = super().rule_start(rule, context)
    return rule_interface

  def finish(self, context: models.Context) -> int:
    # add extra line
    self.print_line()
    return super().finish(context)

  def lint_start(self, context):
    super().lint_start(context)
    self.writer.writeheader()

  def _add_result(self, rule, resource, status, short_info=None, reason=None):
    self.rule_has_results = True
    rule_id = f'{rule.product}/{rule.rule_class}/{rule.rule_id}'
    if reason:
      message = '' + reason
    elif short_info:
      message = '' + short_info
    else:
      message = '-'
    self.writer.writerow({
        'rule': rule_id,
        'resource': resource.full_path if resource else '-',
        'status': status,
        'message': message,
        'doc_url': rule.doc_url
    })

  def add_skipped(self, rule: lint.LintRule, context: models.Context,
                  resource: Optional[models.Resource], reason: str,
                  short_info: Optional[str]):
    super().add_skipped(rule,
                        context,
                        resource,
                        reason=reason,
                        short_info=short_info)
    if not self.show_skipped:
      return
    self._add_result(rule, resource, 'SKIP', short_info, reason)

  def add_ok(self, rule: lint.LintRule, context: models.Context,
             resource: models.Resource, short_info: Optional[str]):
    super().add_ok(rule, context, resource, short_info=short_info)
    if not self.show_ok:
      return
    self._add_result(rule, resource, 'OK', short_info)

  def add_failed(self, rule: lint.LintRule, context: models.Context,
                 resource: models.Resource, reason: Optional[str],
                 short_info: Optional[str]):
    super().add_failed(rule,
                       context,
                       resource,
                       reason=reason,
                       short_info=short_info)
    self._add_result(rule, resource, 'FAIL', short_info, reason)
