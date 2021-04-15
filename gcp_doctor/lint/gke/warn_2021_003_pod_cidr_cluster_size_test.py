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

  def test_run_test(self):
    context = models.Context(projects=[DUMMY_PROJECT_NAME])
    output = io.StringIO()
    report = report_terminal.LintReportTerminal(file=output)
    test = lint.LintTest(
        product='test',
        test_class=lint.LintTestClass.ERR,
        test_id='9999_999',
        short_desc='short description',
        long_desc='long description',
        run_test_f=warn_2021_003_pod_cidr_cluster_size.run_test)
    test_report = report.test_start(test, context)
    test.run_test_f(context, test_report)
    report.test_end(test, context)
    # yapf: disable
    expected_result = (
        '*  test/ERR/9999_999: short description',
        '   - gcpd-gke-1-9b90/europe-west1/gke2'+
        '                                    [ OK ] 3/1024 nodes used.',
        '   - gcpd-gke-1-9b90/europe-west1/gke3'+
        '                                    [ OK ] 3/1024 nodes used.',
        '   - gcpd-gke-1-9b90/europe-west4-a/gke1'

        '                                  [FAIL] 1/1 nodes used.',
        '     Pod CIDR: 192.168.1.0/24. Test threshold: 1 (90%).',
        '',
        '   long description',
        '',
        '',
    )
    assert output.getvalue() == '\n'.join(expected_result)
