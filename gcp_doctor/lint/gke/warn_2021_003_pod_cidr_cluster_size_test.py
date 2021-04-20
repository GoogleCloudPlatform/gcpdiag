# Lint as: python3
"""Test code in err_2020_001_sa_perm.py."""

import io
from unittest import mock

from gcp_doctor import lint, models
from gcp_doctor.lint import report_terminal
from gcp_doctor.lint.gke import warn_2021_003_pod_cidr_cluster_size
from gcp_doctor.queries import gke_stub, iam_stub

DUMMY_PROJECT_NAME = 'gcpd-gke-1-9b90'


def get_api_stub(service_name: str, version: str):
  if service_name == 'container':
    return gke_stub.get_api_stub(service_name, version)
  elif service_name in ['cloudresourcemanager', 'iam']:
    return iam_stub.get_api_stub(service_name, version)
  else:
    raise ValueError(f"I don't know how to mock {service_name}")


@mock.patch('gcp_doctor.queries.apis.get_api', new=get_api_stub)
class Test:

  def test_run_rule(self, snapshot):
    context = models.Context(projects=[DUMMY_PROJECT_NAME])
    output = io.StringIO()
    report = report_terminal.LintReportTerminal(file=output)
    rule = lint.LintRule(
        product='test',
        rule_class=lint.LintRuleClass.ERR,
        rule_id='9999_999',
        short_desc='short description',
        long_desc='long description',
        run_rule_f=warn_2021_003_pod_cidr_cluster_size.run_rule)
    lint_report = report.rule_start(rule, context)
    rule.run_rule_f(context, lint_report)
    report.rule_end(rule, context)
    snapshot.assert_match(output.getvalue(), 'output.txt')
