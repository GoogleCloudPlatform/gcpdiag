# Copyright 2021 Google LLC
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

from unittest import mock

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
