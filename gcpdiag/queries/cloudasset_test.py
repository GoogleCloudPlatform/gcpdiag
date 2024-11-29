# Copyright 2024 Google LLC
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
"""Test code in cloudasset.py."""

from unittest import mock

from gcpdiag import models
from gcpdiag.queries import apis_stub, cloudasset

DUMMY_PROJECT_NAME = 'gcpdiag-cloudasset1-aaaa'
DUMMY_QUERY = 'location:us-central1'
ASSET_TYPE1 = 'compute.googleapis.com/Subnetwork'
ASSET_TYPE2 = 'compute.googleapis.com/Address'


@mock.patch('gcpdiag.queries.apis.get_api', new=apis_stub.get_api_stub)
class TestCloudAsset:
  """Test CloudAsset."""

  def test_search_all_resources(self):
    context = models.Context(project_id=DUMMY_PROJECT_NAME)
    asset_resources = cloudasset.search_all_resources(context.project_id,
                                                      query=DUMMY_QUERY)
    assert len(asset_resources) == 4

    assert ASSET_TYPE1 in [
        resource.asset_type for resource in asset_resources.values()
    ]

    assert ASSET_TYPE2 in [
        resource.asset_type for resource in asset_resources.values()
    ]
