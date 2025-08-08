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

# Lint as: python3
"""Stub API calls used in looker.py for testing.

Instead of doing real API calls, we return test JSON data.
"""

import json
import re

import googleapiclient.errors
import httplib2

from gcpdiag.queries import apis_stub


class LookerApiStub(apis_stub.ApiStub):
  """Mock object to simulate container api calls."""

  def __init__(self, mock_state='looker'):
    self.mock_state = mock_state

  def projects(self):
    return self

  def locations(self):
    return self

  def instances(self):
    return self

  def list(self, parent):
    m = re.match(r'projects/([^/]+)/', parent)
    self.list_page = 1
    project_id = m.group(1)
    return apis_stub.RestCallStub(project_id, 'looker')

  def list_all(self, parent):
    m = re.match(r'projects/([^/]+)/', parent)
    self.list_page = 1
    project_id = m.group(1)
    return apis_stub.RestCallStub(project_id, 'looker')

  def get(self, name):
    m = re.match(r'projects/([^/]+)/locations/([^/]+)/instances/([^/]+)', name)
    if not m:
      raise KeyError('Invalid instance name format')
    project_id = m.group(1)
    self.instance = m.group(3)
    return apis_stub.RestCallStub(project_id, f'instance-{self.instance}')

  def list_next(self, previous_request, previous_response):
    a = previous_request  # pylint: disable=unused-variable
    b = previous_response  # pylint: disable=unused-variable

  def execute(self):

    json_dir = apis_stub.get_json_dir('gcpdiag-looker1-aaaa')
    with open(json_dir / 'looker.json', encoding='utf-8') as json_file:
      response = json.load(json_file)
      services = response['instances']
      name = ''
      for service in services:
        name = service['name']

    if name == '':
      raise googleapiclient.errors.HttpError(httplib2.Response({'status': 404}),
                                             b'Not found')
    else:
      return services
