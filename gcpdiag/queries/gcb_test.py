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
"""Test code in gcb.py."""

from unittest import mock

from gcpdiag import models
from gcpdiag.queries import apis_stub, gcb

DUMMY_PROJECT_NAME = 'gcpdiag-gcb1-aaaa'
DUMMY_CLOUD_BUILD_1_ID = '01ff384c-d7f2-4295-ad68-5c32529d8b85'


@mock.patch('gcpdiag.queries.apis.get_api', new=apis_stub.get_api_stub)
class TestCloudBuild:
  """Test Cloud Build"""

  def test_get_builds(self):
    context = models.Context(project_id=DUMMY_PROJECT_NAME)
    builds = gcb.get_builds(context=context)
    assert len(builds) == 3
    assert DUMMY_CLOUD_BUILD_1_ID in builds
