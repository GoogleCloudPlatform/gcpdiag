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
""" Generalize rule snapshot testing """

import io
from os import path
from unittest import mock

from gcpdiag import lint, models
from gcpdiag.lint import lb, report_terminal
from gcpdiag.queries import apis_stub

DUMMY_PROJECT_NAME = 'gcpdiag-lb1-aaaa'


@mock.patch('gcpdiag.queries.apis.get_api', new=apis_stub.get_api_stub)
class Test:

  def test_all_rules(self, snapshot):

    repo = lint.LintRuleRepository(load_extended=True)
    repo.load_rules(lb)
    context = models.Context(project_id=DUMMY_PROJECT_NAME)
    snapshot.snapshot_dir = path.join(path.dirname(__file__), 'snapshots')
    # run rule one by one to have separated outputs
    for rule in repo.rules:
      output = io.StringIO()
      report = report_terminal.LintReportTerminal(file=output,
                                                  show_skipped=True)
      repo.run_rules(context, report, [
          lint.LintRulesPattern(
              f'{rule.product}/{rule.rule_class}/{rule.rule_id}')
      ])
      snapshot.assert_match(
          output.getvalue(),
          path.join(snapshot.snapshot_dir,
                    f'{rule.rule_class}_{rule.rule_id}.txt'))
