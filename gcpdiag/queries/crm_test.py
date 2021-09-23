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
"""Test code in crm.py."""

from unittest import mock

import diskcache

from gcpdiag.queries import apis_stub, crm

DUMMY_PROJECT_ID = 'gcpd-gke-1-9b90'
DUMMY_PROJECT_NR = 18404348413
DUMMY_PROJECT_NAME = 'gcp-doctor test - gke1'


def get_cache_stub():
  """Use a temporary directory instead of the user cache for testing."""
  return diskcache.Cache()


@mock.patch('gcpdiag.queries.apis.get_api', new=apis_stub.get_api_stub)
@mock.patch('gcpdiag.caching.get_cache', new=get_cache_stub)
class Test:
  """Test project.py"""

  def test_get_project(self):
    p = crm.get_project(DUMMY_PROJECT_ID)
    assert p.id == DUMMY_PROJECT_ID
    assert p.number == DUMMY_PROJECT_NR
    assert p.name == DUMMY_PROJECT_NAME
