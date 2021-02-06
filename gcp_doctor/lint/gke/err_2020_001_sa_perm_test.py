# Lint as: python3
"""Test code in err_2020_001_sa_perm.py."""

import io
from unittest import mock

from gcp_doctor import lint, models
from gcp_doctor.lint import report_terminal
from gcp_doctor.lint.gke import err_2020_001_sa_perm
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

  def test_run_test(self):
    context = models.Context(projects=[DUMMY_PROJECT_NAME])
    output = io.StringIO()
    report = report_terminal.LintReportTerminal(file=output)
    test = lint.LintTest(product='test',
                         test_class='TST',
                         test_id='9999_999',
                         short_desc='short description',
                         long_desc='long description',
                         run_test_f=err_2020_001_sa_perm.run_test)
    test_report = report.test_start(test, context)
    test.run_test_f(context, test_report)
    report.test_end(test, context)
    # yapf: disable
    assert (output.getvalue() == (
        '[test/TST/9999_999]: short description\n'
        '  - gcpd-gke-1-9b90/europe-west1/gke2/default-pool                       [ OK ]\n'
        '  - gcpd-gke-1-9b90/europe-west1/gke3/default-pool                       [FAIL]\n'
        # pylint: disable=line-too-long
        '    missing roles: roles/monitoring.viewer, roles/monitoring.metricWriter, roles/logging.logWriter\n'
        '  - gcpd-gke-1-9b90/europe-west4-a/gke1                                  [SKIP]\n'
        '    monitoring disabled\n\n'
    ))
