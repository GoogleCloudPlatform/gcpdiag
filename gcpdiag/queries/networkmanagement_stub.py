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
import re

from gcpdiag.queries import apis_stub

# pylint: disable=unused-argument
# pylint: disable=invalid-name


class NetworkManagementApiStub:
  """Mock object to simulate compute engine networking api calls.

  This object is created by GceApiStub, not used directly in test scripts.
  """

  def __init__(self, mock_state='init'):
    self.mock_state = mock_state

  def projects(self):
    return self

  def locations(self):
    return self

  def global_(self):
    return self

  def connectivityTests(self):
    return self

  def operations(self):
    return OperationsStub()

  def get(self, name):
    pattern = r'projects/([^/]+)/locations/global/connectivityTests/([^/]+)'
    match = re.search(pattern, name)
    if match:
      project = match.group(1)
      test_id = match.group(2)
      if test_id == 'vmexternalipconnectivitytest':
        return apis_stub.RestCallStub(project, 'connectivity-test')
      else:
        return self
    else:
      raise ValueError('cannot call get method here')

  def create(self, *args, **kwargs):
    return OperationsStub()

  def delete(self, name):
    del name
    return OperationsStub()

  # pylint: disable=redefined-builtin
  def list(self, project, url):
    pattern = r'projects/([^/]+)/locations/global/connectivityTests/([^/]+)'
    match = re.search(pattern, url)
    if match:
      project = match.group(1)
      return apis_stub.RestCallStub(project, 'connectivity-tests')
    else:
      raise ValueError(f'cannot call method {self.mock_state} here')

  # override the apis_stub for delete and create method calls.
  def execute(self, *args):
    return {'name': 'override', 'done': True}


class OperationsStub:
  """Mock object to simulate networkmanagement operation calls.

    This object is not used directly in test scripts.
    """

  def __init__(self):
    pass

  def get(self, name):
    del name
    return self

  def execute(self) -> dict:
    return {'name': 'override', 'done': True}
