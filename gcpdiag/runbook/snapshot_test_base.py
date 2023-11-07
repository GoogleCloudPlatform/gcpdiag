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
""" Base class for snapshot tests """
import io
import sys
from os import path
from unittest import mock

from gcpdiag import models, runbook
from gcpdiag.queries import apis_stub, kubectl_stub


@mock.patch('gcpdiag.queries.apis.get_api', new=apis_stub.get_api_stub)
@mock.patch('gcpdiag.queries.kubectl.verify_auth', new=kubectl_stub.verify_auth)
@mock.patch('gcpdiag.queries.kubectl.check_gke_ingress',
            new=kubectl_stub.check_gke_ingress)
class RulesSnapshotTestBase:
  """ Run snapshot test """

  def test_all_rules(self, snapshot):
    for rule in self._list_rules():
      snapshot.snapshot_dir = path.join(path.dirname(self.rule_pkg.__file__),
                                        'snapshots')
      repo = self._mk_repo(rule=rule)
      output_stream = io.StringIO()
      sys.stdout = output_stream
      repo.run_rules(self._mk_context())
      snapshot.assert_match(
          output_stream.getvalue(),
          path.join(snapshot.snapshot_dir, f'{rule.rule_id}.txt'))

  def _list_rules(self):
    return self._mk_repo().rules_to_run

  def _mk_context(self):
    return models.Context(project_id=self.project_id,
                          parameters=self.rule_parameters)

  def _mk_repo(self, rule=None):
    if rule is None:
      rule_pattern = None
    else:
      rule_pattern = [
          runbook.RunbookRulesPattern(f'{rule.product}/{rule.rule_id}')
      ]
    repo = runbook.RunbookRuleRepository(runbook=rule_pattern)
    repo.load_rules(self.rule_pkg)
    return repo
