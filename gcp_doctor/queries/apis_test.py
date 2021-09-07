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

from gcp_doctor.queries import apis, apis_stub

DUMMY_PROJECT_NAME = 'gcpd-gke-1-9b90'


@mock.patch('gcp_doctor.queries.apis.get_api', new=apis_stub.get_api_stub)
class Test:

  def test_is_enabled(self):
    assert apis.is_enabled(DUMMY_PROJECT_NAME, 'container.googleapis.com')
    assert not apis.is_enabled(DUMMY_PROJECT_NAME,
                               'containerxyz.googleapis.com')
