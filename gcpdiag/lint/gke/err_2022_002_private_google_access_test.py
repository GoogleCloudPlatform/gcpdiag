# Copyright 2022 Google LLC
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
"""Test code in err_2022_002_private_google_access."""

import io
from unittest import mock

from gcpdiag import lint, models
from gcpdiag.lint import report_terminal
from gcpdiag.lint.gke import err_2022_002_private_google_access
from gcpdiag.queries import apis_stub

DUMMY_PROJECT_NAME = 'gcpdiag-gke1-aaaa'


@mock.patch('gcpdiag.queries.apis.get_api', new=apis_stub.get_api_stub)
class Test:

  def test_run_rule(self, snapshot):
    context = models.Context(project_id=DUMMY_PROJECT_NAME)
    output = io.StringIO()
    report = report_terminal.LintReportTerminal(file=output, show_skipped=True)
    rule = lint.LintRule(product='test',
                         rule_class=lint.LintRuleClass.ERR,
                         rule_id='9999_999',
                         short_desc='short description',
                         long_desc='long description',
                         run_rule_f=err_2022_002_private_google_access.run_rule)
    lint_report = report.rule_start(rule, context)
    rule.run_rule_f(context, lint_report)
    report.rule_end(rule, context)
    snapshot.assert_match(output.getvalue(), 'output.txt')
