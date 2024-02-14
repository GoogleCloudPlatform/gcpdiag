"""Base class for snapshot tests"""

import io
from os import path
from unittest import mock

from gcpdiag import lint, models
from gcpdiag.lint.output import terminal_output
from gcpdiag.queries import apis_stub, kubectl_stub


@mock.patch('gcpdiag.queries.apis.get_api', new=apis_stub.get_api_stub)
@mock.patch('gcpdiag.queries.kubectl.verify_auth', new=kubectl_stub.verify_auth)
@mock.patch(
    'gcpdiag.queries.kubectl.check_gke_ingress',
    new=kubectl_stub.check_gke_ingress,
)
class RulesSnapshotTestBase:
  """Run snapshot test"""

  def test_all_rules(self, snapshot):
    for rule in self._list_rules():
      snapshot.snapshot_dir = path.join(path.dirname(self.rule_pkg.__file__),
                                        'snapshots')
      repo = self._mk_repo(rule)
      output_stream = io.StringIO()
      repo.result.add_result_handler(
          self._mk_output(output_stream).result_handler)
      repo.run_rules(self._mk_context())
      snapshot.assert_match(
          output_stream.getvalue(),
          path.join(snapshot.snapshot_dir,
                    f'{rule.rule_class}_{rule.rule_id}.txt'),
      )

  def _list_rules(self):
    return self._mk_repo().rules_to_run

  def _mk_context(self):
    return models.Context(project_id=self.project_id)

  def _mk_output(self, output_stream):
    return terminal_output.TerminalOutput(file=output_stream, show_skipped=True)

  def _mk_repo(self, rule=None):
    if rule is None:
      include = None
    else:
      include = [
          lint.LintRulesPattern(
              f'{rule.product}/{rule.rule_class}/{rule.rule_id}')
      ]
    repo = lint.LintRuleRepository(load_extended=True, include=include)
    repo.load_rules(self.rule_pkg)
    return repo
