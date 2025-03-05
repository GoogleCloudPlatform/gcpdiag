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

  def aggregatedList(self, project):
    if self.mock_state == 'addresses':
      return apis_stub.RestCallStub(project, 'compute-addresses')
    else:
      raise ValueError(f'cannot call method {self.mock_state} here')

  def get(self, project, network=None, region=None, subnetwork=None):
    if not subnetwork:
      return apis_stub.RestCallStub(project, f'compute-network-{network}')
    else:
      self.mock_state = 'get_single_subnetwork'
      self.subnetwork = subnetwork
      self.region = region or SUBNETWORKS_REGION
    self.project_id = project
    return self

  def get_network(self, project, network):
    return apis_stub.RestCallStub(project, f'compute-network-{network}')

  def get_routers(self, project, region, network):
    return apis_stub.RestCallStub(project, f'compute-network-{region}')

  def get_router_by_name(self, project, region, router_name):
    return apis_stub.RestCallStub(project, f'compute-network-{region}')

  def nat_router_status(self, project, router_name, region):
    return apis_stub.RestCallStub(
        project, f'compute-routers-routerStatus-{router_name}')

  def get_nat_ip_info(self, project, router_name, region):
    return apis_stub.RestCallStub(project,
                                  f'compute-routers-rnatIpInfo-{router_name}')

  def getIamPolicy(self, project, region, resource):
    return apis_stub.RestCallStub(project, 'compute-subnetwork-policy')

  def getEffectiveFirewalls(self, project, network):
    return apis_stub.RestCallStub(project,
                                  f'compute-effective-firewalls-{network}')

  # pylint: disable=redefined-builtin
  def list(self, project, region=None, filter=None, fields=None):
    if self.mock_state == 'subnetworks':
      return apis_stub.RestCallStub(
          project, f'compute-subnetworks-{SUBNETWORKS_REGION}')
    elif self.mock_state == 'routers':
      if region:
        return apis_stub.RestCallStub(project, f'compute-routers-{region}')
      return apis_stub.RestCallStub(project,
                                    f'compute-routers-{SUBNETWORKS_REGION}')
    elif self.mock_state == 'networks':
      return apis_stub.RestCallStub(project, 'compute-network-default')
    elif self.mock_state == 'routes':
      return apis_stub.RestCallStub(project, 'compute-network-routes')
    else:
      raise ValueError(f'cannot call method {self.mock_state} here')

  def list_next(self, prev_request, prev_response):
    return None

  def execute(self, num_retries=0):
    json_dir = apis_stub.get_json_dir(self.project_id)
    if self.mock_state == 'get_single_subnetwork':
      with open(json_dir / 'compute-subnetworks-aggregated.json',
                encoding='utf-8') as json_file:
        items = json.load(json_file)['items']
        region = 'regions/' + self.region
        subnets = items[region]['subnetworks']
        subnet_resp = None
        for subnet in subnets:
          if subnet['name'] == self.subnetwork:
            subnet_resp = subnet
            break
        if subnet_resp:
          return subnet_resp
        else:
          raise ValueError(f'cannot call method {self.mock_state} here')

  def getRouterStatus(self, project, router, region):
    if self.mock_state == 'routers':
      return apis_stub.RestCallStub(project,
                                    f'compute-routers-routerStatus-{router}')

  def getNatIpInfo(self, project, router, region):
    if self.mock_state == 'routers':
      return apis_stub.RestCallStub(project,
                                    f'compute-routers-natIpInfo-{router}')
