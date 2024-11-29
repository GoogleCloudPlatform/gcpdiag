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
"""Stub API calls used in cloudasset.py for testing.

Instead of doing real API calls, we return test JSON data.
"""
import re

from gcpdiag.queries import apis_stub

#pylint: disable=unused-argument


class CloudAssetApiStub(apis_stub.ApiStub):
  """Mock object to simulate Cloud Asset api calls."""

  def v1(self):
    return self

  # pylint: disable=invalid-name
  def searchAllResources(self, scope, assetTypes=None, query=None):
    project_id_match = re.match(r'projects/([^/]*)', scope)
    if not project_id_match:
      raise RuntimeError(f"Can't parse scope {scope}")
    project_id = project_id_match.group(1)

    location_match = re.match(r'location:([^/]*)', query)
    if not location_match:
      raise RuntimeError(f"Can't parse query {query}")
    location = location_match.group(1)
    return apis_stub.RestCallStub(project_id,
                                  f'search-all-resources-{location}')
