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

# Lint as: python3
"""Test code in gae.py."""

from unittest import mock

from gcpdiag import models
from gcpdiag.queries import apis_stub, gae

DUMMY_PROJECT_NAME = 'gcpdiag-gaes1-aaaa'


@mock.patch('gcpdiag.queries.apis.get_api', new=apis_stub.get_api_stub)
class TestAppEngine:
  """Test App Engine"""

  def test_get_services(self):
    context = models.Context(project_id=DUMMY_PROJECT_NAME)
    services = gae.get_services(context)
    assert len(services) == 1

  def test_get_versions(self):
    context = models.Context(project_id=DUMMY_PROJECT_NAME)
    versions = gae.get_versions(context)
    assert len(versions) == 1
