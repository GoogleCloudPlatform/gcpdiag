# Copyright 2023 Google LLC
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
"""Test code in apis.py."""

from unittest import TestCase, mock

from gcpdiag import config
from gcpdiag.queries import apis, apis_stub

DUMMY_PROJECT_NAME = 'gcpdiag-gke1-aaaa'


class TestCredential:
  """Test apis set_credentials."""

  def test_set_credential_null(self):
    # pylint:disable=protected-access
    apis._credentials = 'something to clear'
    apis.set_credentials(None)
    assert apis._credentials is None
    # pylint:enable=protected-access

  @mock.patch('google.oauth2.credentials.Credentials.from_authorized_user_info')
  def test_set_credential(self, mock_cred):
    mock_cred.return_value = 'credential_data'
    apis.set_credentials('"some json data"')
    # pylint:disable=protected-access
    assert apis._credentials == 'credential_data'
    # pylint:enable=protected-access


@mock.patch('gcpdiag.queries.apis.get_api', new=apis_stub.get_api_stub)
class Test:
  """Test apis."""

  def test_is_enabled(self):
    assert apis.is_enabled(DUMMY_PROJECT_NAME, 'container')
    assert not apis.is_enabled(DUMMY_PROJECT_NAME, 'containerxyz')

  def test_is_all_enabled(self):
    for value in apis.is_all_enabled(DUMMY_PROJECT_NAME,
                                     ['container', 'compute']).values():
      assert value == 'ENABLED'
    for val in apis.is_all_enabled(DUMMY_PROJECT_NAME,
                                   ['containerxyz', 'computelol']).values():
      assert val == 'DISABLED'


class TestTPC(TestCase):
  """testing for TPC universe domain settings."""

  @mock.patch('gcpdiag.queries.apis.get_credentials')
  @mock.patch('googleapiclient.discovery.build')
  def test_tpc_endpoint(self, mock_build, mock_cred):
    mock_cred.return_value.universe_domain = 'test_domain.goog'
    config.init({'universe_domain': 'test_domain.goog'}, 'x')
    _ = apis.get_api('dataproc', 'v1', 'test_project')
    endpoint = mock_build.call_args[1]['client_options'].api_endpoint
    assert endpoint.endswith('test_domain.goog')

  @mock.patch('gcpdiag.queries.apis.get_credentials')
  @mock.patch('googleapiclient.discovery.build')
  def test_not_tpc_endpoint(self, mock_build, mock_cred):
    mock_cred.return_value.universe_domain = 'googleapis.com'
    config.init({'universe_domain': ''}, 'x')
    _ = apis.get_api('composer', 'v1', 'test_project')
    endpoint = mock_build.call_args[1]['client_options'].api_endpoint
    assert endpoint == 'https://composer.googleapis.com'

  @mock.patch('gcpdiag.queries.apis._get_credentials_adc')
  @mock.patch('googleapiclient.discovery.build')
  def test_universe_mismatch(self, mock_build, mock_cred):
    del mock_build
    mock_cred.return_value.universe_domain = 'googleapis.com.not'
    config.init({'universe_domain': 'a_mismatching_universe'}, 'x')
    with self.assertRaises(ValueError):
      _ = apis.get_api('composer', 'v1', 'test_project')
