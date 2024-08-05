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

import json

import apiclient.errors
import httplib2

from gcpdiag.queries import apis_stub

# pylint: disable=unused-argument
# pylint: disable=invalid-name

backend_service_states = ('backendServices', 'regionBackendServices')


class LbApiStub:
  """Mock object to simulate compute engine networking api calls.

  This object is created by GceApiStub, not used directly in test scripts.
  """

  def __init__(self, mock_state):
    self.mock_state = mock_state

  def aggregatedList(self, project):
    if self.mock_state == 'forwardingRules':
      return apis_stub.RestCallStub(project, 'forwardingRules')
    else:
      raise ValueError(f'cannot call method {self.mock_state} here')

  # pylint: disable=redefined-builtin
  def list(self, project, region=None):
    if self.mock_state == 'backendServices':
      return apis_stub.RestCallStub(project, 'backendServices')
    if self.mock_state == 'regionBackendServices':
      return apis_stub.RestCallStub(project, f'regionBackendServices-{region}')
    else:
      raise ValueError(f'cannot call method {self.mock_state} here')

  def get(self, project, backendService=None, region=None):
    if self.mock_state in backend_service_states and backendService:
      self.backend_service = backendService
      self.region = region
      self.project = project
      return self
    else:
      raise ValueError(f'cannot call method {self.mock_state} here')

  def getHealth(self, project, backendService, body, region=None):
    backend_url_parts = body.get('group').split('/')
    backend_name, backend_type, backend_scope = (
        backend_url_parts[-1],
        backend_url_parts[-2],
        backend_url_parts[-3],
    )

    if self.mock_state == 'backendServices':
      stub_name = (f'backendService-{backendService}-get-health-{backend_type}-'
                   f'{backend_name}-{backend_scope}')
      return apis_stub.RestCallStub(project, stub_name)
    if self.mock_state == 'regionBackendServices':
      stub_name = (f'regionBackendService-{backendService}-{region}-get-health-'
                   f'{backend_type}-{backend_name}-{backend_scope}')
      return apis_stub.RestCallStub(project, stub_name)
    else:
      raise ValueError(f'cannot call method {self.mock_state} here')

  def execute(self, num_retries=0):
    json_dir = apis_stub.get_json_dir(self.project)
    json_file_name = f'{self.mock_state}.json'
    if self.region:
      json_file_name = f'{self.mock_state}-{self.region}.json'
    with open(json_dir / f'{json_file_name}', encoding='utf-8') as json_file:
      resources = json.load(json_file)['items']
      # search for and get the health check
      if self.mock_state in backend_service_states and resources:
        for backend_service in resources:
          if backend_service['name'] == self.backend_service:
            return backend_service
          else:
            raise apiclient.errors.HttpError(
                httplib2.Response({
                    'status': 404,
                    'reason': 'Not Found'
                }),
                f'The backend service {self.backend_service} is not found'.
                encode(),
            )
      else:
        raise ValueError(f'cannot call method {self.mock_state} here')

  def list_next(self, prev_request, prev_response):
    return None
