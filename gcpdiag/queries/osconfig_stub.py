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

# Lint as: python3
"""Stub API calls used in osconfig.py for testing.

Instead of doing real API calls, we return test JSON data.
"""

import re

from gcpdiag.queries import apis_stub

# pylint: disable=unused-argument
# pylint: disable=invalid-name

DUMMY_PROJECT_NAME = 'gcpdiag-osconfig1-aaaa'
DUMMY_NON_EXISTENT_INSTANCE_NAME = 'instance-does-not-exist'


class OSConfigStub:
  """Mock object to simulate osconfig api calls."""

  def __init__(self, mock_state='init'):
    self.mock_state = mock_state

  def projects(self):
    return self

  def locations(self):
    return self

  def instances(self):
    return self

  def inventories(self):
    self.mock_state = 'inventory'
    return self

  def get(self, name, **kwargs):
    m = re.match(r'([\w].+)/instances/([^/]+)', name)
    instance_name = m.group(2)
    if self.mock_state == 'inventory':
      stub = apis_stub.RestCallStub(DUMMY_PROJECT_NAME, 'inventory')
      if instance_name == DUMMY_NON_EXISTENT_INSTANCE_NAME:
        stub.fail_next(1, 404)
      return stub
    else:
      raise ValueError('incorrect value received')
