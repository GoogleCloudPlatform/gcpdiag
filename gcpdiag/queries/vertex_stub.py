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

# Lint as: python3
"""Stub API calls used in vertex.py for testing.

Instead of doing real API calls, we return test JSON data.
"""

import re

from gcpdiag.queries import apis_stub

# pylint: disable=unused-argument
# pylint: disable=invalid-name

NO_FEATURESTORE_NAME_ERROR = \
  'Not able to call {} without setting featurestore name for API.'


class VertexApiStub:
  """Mock object to simulate aiplatform (vertex) api calls."""

  def __init__(self, mock_state='init'):
    self.mock_state = mock_state

  def projects(self):
    return self

  def locations(self):
    return self

  def featurestores(self):
    self.mock_state = 'featurestores'
    return self

  def list(self, parent):
    m = re.match(r'projects/([^/]+)', parent)
    project_id = m.group(1)
    if self.mock_state == 'featurestores':
      return apis_stub.RestCallStub(project_id, 'featurestores')
    else:
      raise ValueError('incorrect value received')
