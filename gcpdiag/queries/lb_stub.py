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
"""Stub API calls used in lb.py for testing.

Instead of doing real API calls, we return test JSON data.
"""

from gcpdiag.queries import apis_stub

# pylint: disable=unused-argument
# pylint: disable=invalid-name


class LbApiStub:
  """Mock object to simulate compute engine networking api calls.

  This object is created by GceApiStub, not used directly in test scripts.
  """

  def __init__(self, mock_state):
    self.mock_state = mock_state

  # pylint: disable=redefined-builtin
  def list(self, project, region=None):
    project = 'gcpdiag-lb1-aaaa'
    if self.mock_state == 'backendServices':
      return apis_stub.RestCallStub(project, 'backendServices')
    else:
      raise ValueError(f'cannot call method {self.mock_state} here')

  def list_next(self, prev_request, prev_response):
    return None
