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

# Lint as: python3
"""Stub API calls used in gcf.py for testing.

Instead of doing real API calls, we return test JSON data.
"""

import re

from gcpdiag.queries import apis_stub

# pylint: disable=unused-argument
# pylint: disable=invalid-name
INCORRECT_RESOURCE_ERROR = ('incorrect resource format. Use '
                            'projects/*/locations/*/repositories/')


class ArtifactRegistryApiStub:
  """Mock object to simulate function api calls."""

  def projects(self):
    return self

  def locations(self):
    return self

  def repositories(self):
    return self

  def getIamPolicy(self, resource: str) -> apis_stub.RestCallStub:
    m = re.match(r'projects/([^/]+)/locations/([^/]+)/repositories/([^/]+)',
                 resource)
    if m:
      project_id = m.group(1)
      return apis_stub.RestCallStub(project_id, 'artifact-registry-policy.json')
    else:
      raise ValueError(INCORRECT_RESOURCE_ERROR)
