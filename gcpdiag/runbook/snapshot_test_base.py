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
import textwrap
from os import path
from unittest import mock

from gcpdiag import models, runbook
from gcpdiag.queries import apis_stub, kubectl_stub
from gcpdiag.runbook import command, util


@mock.patch('gcpdiag.queries.apis.get_api', new=apis_stub.get_api_stub)
@mock.patch('gcpdiag.queries.kubectl.verify_auth', new=kubectl_stub.verify_auth)
@mock.patch('gcpdiag.queries.kubectl.check_gke_ingress',
            new=kubectl_stub.check_gke_ingress)
class RulesSnapshotTestBase:
  """ Run snapshot test """

  def test_all_rules(self, snapshot):
    self.de = runbook.DiagnosticEngine()
    for rule in self._list_rules():
      snapshot.snapshot_dir = path.join(path.dirname(self.rule_pkg.__file__),
                                        'snapshots')
      output_stream = io.StringIO()
      sys.stdout = output_stream
      for parameter in self.rule_parameters:
        context = self._mk_context(parameter=parameter)
        self.de.dt = rule
        print(textwrap.fill(str(context), 100), file=sys.stdout, end='\n\n')
        self.de.run_diagnostic_tree(context)
        print('\n')
      snapshot.assert_match(
          output_stream.getvalue(),
          path.join(
              snapshot.snapshot_dir,
              f'{util.pascal_case_to_snake_case(rule(None).__class__.__name__)}.txt'
          ))

  def _mk_context(self, parameter):
    return models.Context(project_id=self.project_id, parameters=parameter)

  def _list_rules(self):
    #pylint: disable=protected-access
    command._load_runbook_rules(self.rule_pkg.__name__)
    return runbook.DiagnosticTreeRegister.values()
