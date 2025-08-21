# Copyright 2025 Google LLC
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
"""Stub API calls used in looker.py for testing."""

import json
import re
from datetime import datetime, timezone

import googleapiclient.errors
import httplib2

from gcpdiag.queries import apis_stub

DUMMY_PROJECT_NAME_FOR_STUB = 'gcpdiag-looker1-aaaa'
DUMMY_OP_LOCATION = 'us-central1'
DUMMY_OP_ID = 'operation-1'


class LookerApiStub(apis_stub.ApiStub):
  """Mock object for the Looker API."""

  def __init__(self, project_id=None):
    super().__init__()
    self.project_id = project_id or DUMMY_PROJECT_NAME_FOR_STUB
    self._resource_type = None

  class _HttpRequest:

    def __init__(self, stub, resource_type, method, kwargs):
      self._stub = stub
      self._resource_type = resource_type
      self._method = method
      self._kwargs = kwargs

    def execute(self, num_retries=0):
      return self._stub.execute_request(self._resource_type, self._method,
                                        self._kwargs, num_retries)

  def projects(self):
    return self

  def locations(self):
    self._resource_type = 'locations'
    return self

  def instances(self):
    self._resource_type = 'instances'
    return self

  def operations(self):
    self._resource_type = 'operations'
    return self

  def list(self, **kwargs):
    if self._resource_type == 'instances':
      return apis_stub.RestCallStub(self.project_id, 'looker-instances')
    return self._HttpRequest(self, self._resource_type, 'list', kwargs)

  def get(self, **kwargs):
    if self._resource_type == 'instances':
      name = kwargs.get('name')
      m = re.match(r'projects/([^/]+)/locations/([^/]+)/instances/([^/]+)',
                   name)
      if not m:
        raise KeyError('Invalid instance name format')
      return apis_stub.RestCallStub(self.project_id, f'instance-{m.group(3)}')
    return self._HttpRequest(self, self._resource_type, 'get', kwargs)

  def get_operations(self, **kwargs):
    return self._HttpRequest(self, 'operations', 'get', kwargs)


# pylint: disable=useless-return

  def list_next(self, previous_request, previous_response=None):
    _, _ = previous_request, previous_response
    return None

  def execute_request(self, resource_type, method, kwargs, num_retries=0):
    _ = num_retries

    if resource_type == 'locations' and method == 'list':
      parent_path = kwargs.get('name') or f'projects/{self.project_id}'
      return {
          'locations': [{
              'name': f'{parent_path}/locations/{DUMMY_OP_LOCATION}',
              'locationId': DUMMY_OP_LOCATION
          }, {
              'name': f'{parent_path}/locations/europe-west1',
              'locationId': 'europe-west1'
          }]
      }

    if resource_type == 'operations' and method == 'list':
      ops = []
      parent_path = kwargs.get('name')
      if parent_path and DUMMY_OP_LOCATION in parent_path:
        project_id = parent_path.split('/')[1]
        ops.append({
            'name': (f'projects/{project_id}/locations/{DUMMY_OP_LOCATION}/'
                     f'operations/{DUMMY_OP_ID}'),
            'metadata': {
                'verb': 'update'
            },
            'done': False
        })
      return {'operations': ops}

    if resource_type == 'operations' and method == 'get':
      request_path = kwargs.get('name') or ''
      if DUMMY_OP_ID in request_path and DUMMY_OP_LOCATION in request_path:
        project_id = request_path.split('/')[1]
        op_path = (
            f'projects/{project_id}/locations/{DUMMY_OP_LOCATION}/operations/{DUMMY_OP_ID}'
        )
        target_path = (f'projects/{project_id}/locations/'
                       f'{DUMMY_OP_LOCATION}/instances/'
                       f'gcpdiag-test-01/databases/'
                       f'my-db')
        return {
            'name': op_path,
            'metadata': {
                'createTime': datetime.now(timezone.utc).isoformat(),
                'target': target_path,
                'verb': 'update'
            },
            'done': True,
            'response': {}
        }
      raise googleapiclient.errors.HttpError(
          httplib2.Response({'status': 404}),
          b'Operation not found by GET stub')

    raise NotImplementedError(
        f'API call not stubbed in LookerApiStub.execute_request: '
        f'resource_type={resource_type}, method={method}')


class LookerInstanceRestCallStub(apis_stub.RestCallStub):
  """Mock object to simulate api calls for Looker instances."""

  def execute(self, num_retries=0):
    _ = num_retries
    json_dir = apis_stub.get_json_dir(self.project_id)
    try:
      with open(json_dir / 'looker-instances.json',
                encoding='utf-8') as json_file:
        return json.load(json_file)
    except FileNotFoundError as exc:
      raise googleapiclient.errors.HttpError(httplib2.Response({'status': 404}),
                                             b'File not found') from exc
