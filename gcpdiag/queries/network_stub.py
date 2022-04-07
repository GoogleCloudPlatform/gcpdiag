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
      return apis_stub.RestCallStub(project, f'compute-network-{network}.json')
    else:
      self.mock_state = 'get_single_subnetwork'
      self.subnetwork = subnetwork
    self.project_id = project
    return self

  def getIamPolicy(self, project, region, resource):
    return apis_stub.RestCallStub(project, 'compute-subnetwork-policy.json')

  def getEffectiveFirewalls(self, project, network):
    return apis_stub.RestCallStub(
        project, f'compute-effective-firewalls-{network}.json')

  # pylint: disable=redefined-builtin
  def list(self, project, region, filter=None, fields=None):
    if self.mock_state == 'subnetworks':
      return apis_stub.RestCallStub(
          project, f'compute-subnetworks-{SUBNETWORKS_REGION}.json')
    elif self.mock_state == 'routers':
      return apis_stub.RestCallStub(
          project, f'compute-routers-{SUBNETWORKS_REGION}.json')
    else:
      raise ValueError(f'cannot call method {self.mock_state} here')

  def list_next(self, prev_request, prev_response):
    return None

  def execute(self, num_retries=0):
    json_dir = apis_stub.get_json_dir(self.project_id)
    if self.mock_state == 'get_single_subnetwork':
      with open(json_dir / f'compute-subnetworks-{SUBNETWORKS_REGION}.json',
                encoding='utf-8') as json_file:
        for subnet in json.load(json_file)['items']:
          if subnet['name'] == self.subnetwork:
            return subnet
    else:
      raise ValueError(f'cannot call method {self.mock_state} here')
