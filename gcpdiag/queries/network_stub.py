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
"""Stub API calls used in network.py for testing.

Instead of doing real API calls, we return test JSON data.
"""

import json

from gcpdiag.queries import apis_stub

# pylint: disable=unused-argument
# pylint: disable=invalid-name

SUBNETWORKS_REGION = 'europe-west4'


class NetworkApiStub:
  """Mock object to simulate compute engine networking api calls.

  This object is created by GceApiStub, not used directly in test scripts."""

  def __init__(self, mock_state):
    self.mock_state = mock_state

  def get(self, project, network=None, region=None, subnetwork=None):
    if not subnetwork:
      self.mock_state = 'get'
      self.network = network
    else:
      self.mock_state = 'get_single_subnetwork'
      self.subnetwork = subnetwork
    self.project_id = project
    return self

  def getIamPolicy(self, project, region, resource):
    self.mock_state = 'getIamPolicy_subnetwork'
    self.project_id = project
    self.subnetwork = resource
    return self

  def getEffectiveFirewalls(self, project, network):
    self.mock_state = 'get_effective_firewalls'
    self.project_id = project
    self.network = network
    return self

  # pylint: disable=redefined-builtin
  def list(self, project, region, filter=None, fields=None):
    self.project_id = project
    if self.mock_state == 'subnetworks':
      return self
    elif self.mock_state == 'routers':
      return self
    else:
      raise ValueError(f'cannot call method {self.mock_state} here')

  def list_next(self, prev_request, prev_response):
    return None

  def execute(self, num_retries=0):
    json_dir = apis_stub.get_json_dir(self.project_id)
    if self.mock_state == 'get':
      with open(json_dir / f'compute-network-{self.network}.json',
                encoding='utf-8') as json_file:
        return json.load(json_file)
    elif self.mock_state == 'get_effective_firewalls':
      with open(json_dir / f'compute-effective-firewalls-{self.network}.json',
                encoding='utf-8') as json_file:
        return json.load(json_file)
    elif self.mock_state == 'subnetworks':
      with open(json_dir / f'compute-subnetworks-{SUBNETWORKS_REGION}.json',
                encoding='utf-8') as json_file:
        return json.load(json_file)
    elif self.mock_state == 'get_single_subnetwork':
      with open(json_dir / f'compute-subnetworks-{SUBNETWORKS_REGION}.json',
                encoding='utf-8') as json_file:
        for subnet in json.load(json_file)['items']:
          if subnet['name'] == self.subnetwork:
            return subnet
    elif self.mock_state == 'getIamPolicy_subnetwork':
      with open(json_dir / 'compute-subnetwork-policy.json',
                encoding='utf-8') as json_file:
        return json.load(json_file)
    elif self.mock_state == 'routers':
      with open(json_dir / f'compute-routers-{SUBNETWORKS_REGION}.json',
                encoding='utf-8') as json_file:
        return json.load(json_file)
    else:
      raise ValueError(f'cannot call method {self.mock_state} here')
