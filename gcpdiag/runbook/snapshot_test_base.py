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
from gcpdiag.queries import apis_stub, dns_stub, kubectl_stub
from gcpdiag.runbook import command, util


@mock.patch('gcpdiag.queries.apis.get_user_email',
            new=lambda: 'fake-user@google.com')
@mock.patch('gcpdiag.queries.apis.get_api', new=apis_stub.get_api_stub)
@mock.patch('gcpdiag.queries.kubectl.verify_auth', new=kubectl_stub.verify_auth)
@mock.patch('gcpdiag.queries.kubectl.check_gke_ingress',
            new=kubectl_stub.check_gke_ingress)
@mock.patch('gcpdiag.queries.dns.find_dns_records',
            new=dns_stub.find_dns_records)
class RulesSnapshotTestBase:
  """ Run snapshot test """

  def test_all_rules(self, snapshot):
    self.de = runbook.DiagnosticEngine()
    tree = self.de.load_tree(self.runbook_name)
    snapshot.snapshot_dir = path.join(path.dirname(self.rule_pkg.__file__),
                                      'snapshots')
    output_stream = io.StringIO()
    sys.stdout = _Tee(output_stream, sys.stdout)
    for parameter in self.rule_parameters:
      parameters = self._mk_parameters(parameter=parameter)
      print(textwrap.fill(str(parameters), 100), file=sys.stdout, end='\n\n')
      self.de.run_diagnostic_tree(tree(), parameter=parameters)
      print('\n')
    snapshot.assert_match(
        output_stream.getvalue(),
        path.join(
            snapshot.snapshot_dir,
            f'{util.pascal_case_to_snake_case(tree().__class__.__name__)}.txt'))

  def _mk_parameters(self, parameter):
    return models.Parameter(parameter)


class _Tee:
  """Helper class to direct the same output to two file like objects at the same time."""

  def __init__(self, string_io1, string_io2):
    self.string_io1 = string_io1
    self.string_io2 = string_io2

  def write(self, data):
    self.string_io1.write(data)
    self.string_io2.write(data)

  def flush(self):
    self.string_io1.flush()
    self.string_io2.flush()


#pylint: disable=protected-access
command._load_runbook_rules(runbook.__name__)
