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
"""Stub API calls used in notebooks.py for testing.

Instead of doing real API calls, we return test JSON data.
"""

import json
import re

from gcpdiag.queries import apis_stub

# pylint: disable=unused-argument
# pylint: disable=invalid-name

NO_INSTANCE_NAME_ERROR = \
  'Not able to call {} without setting instance name for API.'

NO_RUNTIME_NAME_ERROR = \
  'Not able to call {} without setting runtime name for API.'


class NotebooksApiStub:
  """Mock object to simulate notebooks api calls."""

  def __init__(self, mock_state='init'):
    self.mock_state: str = mock_state
    self.project_id: str = ''
    self.instance_name: str = ''
    self.zone: str = ''

  def projects(self):
    return self

  def locations(self):
    return self

  def instances(self):
    self.mock_state = 'instances'
    return self

  def runtimes(self):
    self.mock_state = 'runtimes'
    return self

  def list(self, parent):
    m = re.match(r'projects/([^/]+)', parent)
    project_id = m.group(1)
    if self.mock_state == 'instances':
      return apis_stub.RestCallStub(project_id, 'instances')
    if self.mock_state == 'runtimes':
      return apis_stub.RestCallStub(project_id, 'runtimes')
    else:
      raise ValueError('incorrect value received')

  def get(self, name):
    m = re.match(r'projects/([^/]+)/locations/([^/]+)/instances/([^/]+)', name)
    project_id = m.group(1)
    zone = m.group(2)
    instance_name = m.group(3)
    if self.mock_state == 'instances':
      if instance_name:
        self.mock_state = 'get_single_instance'
        self.instance_name = instance_name
        self.name = name
        self.project_id = project_id
        self.zone = zone
        return self
    raise ValueError(f'incorrect value received: {name}')

  def getInstanceHealth(self, name):
    m = re.match(r'projects/([^/]+)/locations/([^/]+)/instances/([^/]+)', name)
    if m:
      project_id = m.group(1)
      return apis_stub.RestCallStub(project_id, 'health-state')
    else:
      raise ValueError(f'incorrect value received for instance name: {name}')

  def isUpgradeable(self, notebookInstance):
    m = re.match(r'projects/([^/]+)/locations/([^/]+)/instances/([^/]+)',
                 notebookInstance)
    if m:
      project_id = m.group(1)
      return apis_stub.RestCallStub(project_id, 'is-upgradeable')
    else:
      raise ValueError(
          f'incorrect value received for notebookInstance: {notebookInstance}')

  def execute(self, num_retries=0):
    json_dir = apis_stub.get_json_dir(self.project_id)
    if self.mock_state == 'get_single_instance':
      with open(json_dir / 'workbench-instances.json',
                encoding='utf-8') as json_file:
        instances = json.load(json_file)['instances']
        for instance in instances:
          if instance['name'] == self.name:
            return instance

  def checkUpgradability(self, notebookInstance):
    m = re.match(r'projects/([^/]+)/locations/([^/]+)/instances/([^/]+)',
                 notebookInstance)
    if m:
      project_id = m.group(1)
      return apis_stub.RestCallStub(
          project_id, 'notebooks2instance-ok-check-upgradability')
    else:
      raise ValueError(
          f'incorrect value received for instance name: {notebookInstance}')
