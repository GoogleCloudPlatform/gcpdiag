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
"""Generalize rule snapshot testing"""

import base64
import datetime
import io
from os import path
from unittest import mock

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID

from gcpdiag.lint import gke, snapshot_test_base
from gcpdiag.queries import apis_stub, kubectl_stub, web_stub
from gcpdiag.queries import gke as gke_queries
from gcpdiag.queries.generic_api.api_build import generic_api_stub


class MockDate(datetime.date):
  @classmethod
  def today(cls):
    return datetime.date(2026, 6, 1)


class FrozenDateTime(datetime.datetime):
  @classmethod
  def now(cls, tz=None):
    if tz:
      return datetime.datetime(2023, 2, 6, tzinfo=tz)
    else:
      return datetime.datetime(2023, 2, 6)


def _generate_mock_cert(valid_days, expired=False, base_date=None):
  private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
  subject = issuer = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, 'Mock CA')])
  if base_date is None:
    base_date = datetime.datetime.now(datetime.timezone.utc)
  if expired:
    not_before = base_date - datetime.timedelta(days=valid_days + 10)
    not_after = base_date - datetime.timedelta(days=10)
  else:
    not_before = base_date - datetime.timedelta(days=10)
    not_after = base_date + datetime.timedelta(days=valid_days)

  cert = (
    x509.CertificateBuilder()
    .subject_name(subject)
    .issuer_name(issuer)
    .public_key(private_key.public_key())
    .serial_number(x509.random_serial_number())
    .not_valid_before(not_before)
    .not_valid_after(not_after)
    .sign(private_key, hashes.SHA256())
  )

  return cert.public_bytes(serialization.Encoding.PEM).decode('utf-8')


@mock.patch('gcpdiag.queries.web.get', new=web_stub.get)
@mock.patch('gcpdiag.queries.apis.get_api', new=apis_stub.get_api_stub)
@mock.patch('gcpdiag.queries.kubectl.verify_auth', new=kubectl_stub.verify_auth)
@mock.patch(
  'gcpdiag.queries.kubectl.check_gke_ingress',
  new=kubectl_stub.check_gke_ingress,
)
@mock.patch(
  'gcpdiag.queries.generic_api.api_build.get_generic.get_generic_api',
  new=generic_api_stub.get_generic_api_stub,
)
@mock.patch('gcpdiag.lint.gke.err_2026_001_gke_version_support.date', new=MockDate)
class Test(snapshot_test_base.RulesSnapshotTestBase):
  rule_pkg = gke
  project_id = 'gcpdiag-gke1-aaaa'

  def _list_rules(self):
    rules = super()._list_rules()
    return [r for r in rules if not (r.rule_class.value == 'BP' and r.rule_id == '2026_001')]

  def test_all_rules(self, snapshot):
    for rule in self._list_rules():
      snapshot.snapshot_dir = path.join(path.dirname(self.rule_pkg.__file__), 'snapshots')
      repo = self._mk_repo(rule)
      output_stream = io.StringIO()
      repo.result.add_result_handler(self._mk_output(output_stream).result_handler)

      if rule.rule_id == '2026_002' and rule.rule_class.value == 'ERR':
        fixed_now = datetime.datetime(2026, 5, 14, 19, 29, 23, tzinfo=datetime.timezone.utc)

        def mock_cluster_ca_certificate(self_obj):
          if self_obj.name.endswith('gke1') or 'expired' in self_obj.name:
            pem = _generate_mock_cert(valid_days=15, base_date=fixed_now)
            return base64.b64encode(pem.encode('utf-8')).decode('utf-8')
          elif self_obj.name.endswith('gke2'):
            pem1 = _generate_mock_cert(valid_days=15, base_date=fixed_now)
            pem2 = _generate_mock_cert(valid_days=300, base_date=fixed_now)
            bundle = pem1 + pem2
            return base64.b64encode(bundle.encode('utf-8')).decode('utf-8')
          else:
            pem = _generate_mock_cert(valid_days=300, base_date=fixed_now)
            return base64.b64encode(pem.encode('utf-8')).decode('utf-8')

        with mock.patch.object(
          gke_queries.Cluster,
          'cluster_ca_certificate',
          property(mock_cluster_ca_certificate),
        ):
          with mock.patch(
            'gcpdiag.lint.gke.err_2026_002_credential_rotation._get_now',
            return_value=fixed_now,
          ):
            repo.run_rules(self._mk_context())
      else:
        repo.run_rules(self._mk_context())

      snapshot.assert_match(
        output_stream.getvalue(),
        path.join(snapshot.snapshot_dir, f'{rule.rule_class}_{rule.rule_id}.txt'),
      )


class TestGke5(snapshot_test_base.RulesSnapshotTestBase):
  rule_pkg = gke
  project_id = 'gcpdiag-gke5-aaaa'

  def _list_rules(self):
    rules = super()._list_rules()
    return [r for r in rules if r.rule_class.value == 'BP' and r.rule_id == '2026_001']

  def test_all_rules(self, snapshot):
    with mock.patch(
      'gcpdiag.lint.gke.bp_2026_001_maintenance_policy.datetime',
      FrozenDateTime,
    ):
      super().test_all_rules(snapshot)
