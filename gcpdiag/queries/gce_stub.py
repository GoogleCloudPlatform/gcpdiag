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
"""Stub API calls used in gce.py for testing.

Instead of doing real API calls, we return test JSON data.
"""

import json

from gcpdiag.queries import apis_stub, network_stub

# pylint: disable=unused-argument


class ListRegionsQuery:

  def __init__(self, project_id):
    self.project_id = project_id

  def execute(self, num_retries=0):
    json_dir = apis_stub.get_json_dir(self.project_id)
    with open(json_dir / 'compute-regions.json', encoding='utf-8') as json_file:
      return json.load(json_file)


class ComputeEngineApiStubRegions:

  def list(self, project):
    return ListRegionsQuery(project_id=project)


class ComputeEngineApiStub:
  """Mock object to simulate compute engine api calls."""

  # mocked methods:
  # gce_api.zones().list(project=project_id).execute()
  # gce_api.zones().list_next(request, response)
  # op1=gce_api.instances().list(project=pid, zone=z)
  # gce_api.new_batch_http_request().add(op1, callback=cb, request_id=id).execute()
  # gce_api.instanceGroupManagers().list(project=project_id, zone=zone)

  def __init__(self, mock_state='init', project_id=None, zone=None, page=1):
    self.mock_state = mock_state
    self.project_id = project_id
    self.zone = zone
    self.page = page

  def regions(self):
    return ComputeEngineApiStubRegions()

  def zones(self):
    return ComputeEngineApiStub('zones')

  def list(self, project, zone=None):
    return ComputeEngineApiStub(self.mock_state, project_id=project, zone=zone)

  def list_next(self, request, response):
    if self.mock_state == 'instances' and request.zone == 'europe-west1-b' and request.page == 1:
      return ComputeEngineApiStub(mock_state='instances',
                                  project_id=request.project_id,
                                  zone=request.zone,
                                  page=request.page + 1)
    else:
      return None

  def instances(self):
    return ComputeEngineApiStub('instances')

  # pylint: disable=invalid-name
  def instanceGroupManagers(self):
    return ComputeEngineApiStub('migs')

  def new_batch_http_request(self):
    return apis_stub.BatchRequestStub()

  def get(self, project):
    self.project_id = project
    return self

  def projects(self):
    return ComputeEngineApiStub('projects')

  def networks(self):
    return network_stub.NetworkApiStub()

  def execute(self, num_retries=0):
    json_dir = apis_stub.get_json_dir(self.project_id)
    page_suffix = ''
    if self.page > 1:
      page_suffix = f'-{self.page}'
    if self.mock_state == 'regions':
      with open(json_dir / 'compute-regions.json',
                encoding='utf-8') as json_file:
        return json.load(json_file)
    if self.mock_state == 'zones':
      with open(json_dir / 'compute-zones.json', encoding='utf-8') as json_file:
        return json.load(json_file)
    elif self.mock_state == 'projects':
      with open(json_dir / 'compute-project.json',
                encoding='utf-8') as json_file:
        return json.load(json_file)
    elif self.mock_state == 'instances':
      try:
        with open(json_dir / f'compute-instances-{self.zone}{page_suffix}.json',
                  encoding='utf-8') as json_file:
          return json.load(json_file)
      except FileNotFoundError:
        with open(json_dir / 'compute-instances-empty.json',
                  encoding='utf-8') as json_file:
          return json.load(json_file)
    elif self.mock_state == 'migs':
      try:
        with open(json_dir / f'compute-migs-{self.zone}{page_suffix}.json',
                  encoding='utf-8') as json_file:
          return json.load(json_file)
      except FileNotFoundError:
        with open(json_dir / 'compute-migs-empty.json',
                  encoding='utf-8') as json_file:
          return json.load(json_file)
    else:
      raise ValueError("can't call this method here")
