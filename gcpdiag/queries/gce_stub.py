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

from gcpdiag.queries import apis_stub, network_stub

# pylint: disable=unused-argument
# pylint: disable=invalid-name


class ComputeEngineApiStub(apis_stub.ApiStub):
  """Mock object to simulate compute engine api calls."""

  # mocked methods:
  # gce_api.zones().list(project=project_id).execute()
  # gce_api.zones().list_next(request, response)
  # op1=gce_api.instances().list(project=pid, zone=z)
  # gce_api.new_batch_http_request().add(op1, callback=cb, request_id=id).execute()
  # gce_api.instanceGroupManagers().list(project=project_id, zone=zone)
  # gce_api.instanceGroups().list(project=project_id, zone=zone)

  def __init__(self, mock_state='init', project_id=None, zone=None, page=1):
    self.mock_state = mock_state
    self.project_id = project_id
    self.zone = zone
    self.page = page

  def regions(self):
    return ComputeEngineApiStub('regions')

  def zones(self):
    return ComputeEngineApiStub('zones')

  def list(self, project, zone=None, returnPartialSuccess=None, fields=None):
    # TODO: implement fields filtering
    if self.mock_state in ['igs', 'instances', 'migs']:
      return apis_stub.RestCallStub(project,
                                    f'compute-{self.mock_state}-{zone}',
                                    default=f'compute-{self.mock_state}-empty')
    elif self.mock_state in ['regions', 'templates', 'zones']:
      return apis_stub.RestCallStub(project, f'compute-{self.mock_state}')
    else:
      raise RuntimeError(f"can't list for mock state {self.mock_state}")

  def list_next(self, previous_request, previous_response):
    if isinstance(previous_response,
                  dict) and previous_response.get('nextPageToken'):
      return apis_stub.RestCallStub(
          project_id=previous_request.project_id,
          json_basename=previous_request.json_basename,
          page=previous_request.page + 1)
    else:
      return None

  def instances(self):
    return ComputeEngineApiStub('instances')

  def instanceGroupManagers(self):
    return ComputeEngineApiStub('migs')

  def instanceGroups(self):
    return ComputeEngineApiStub('igs')

  def instanceTemplates(self):
    return ComputeEngineApiStub('templates')

  def new_batch_http_request(self):
    batch_api = apis_stub.BatchRequestStub()
    if self._fail_count:
      batch_api.fail_next(self._fail_count, self._fail_status)
      self._fail_count = 0
    return batch_api

  def get(self, project):
    if self.mock_state == 'projects':
      return apis_stub.RestCallStub(project, 'compute-project')

  def projects(self):
    return ComputeEngineApiStub('projects')

  def networks(self):
    return network_stub.NetworkApiStub(mock_state='networks')

  def subnetworks(self):
    return network_stub.NetworkApiStub(mock_state='subnetworks')

  def routers(self):
    return network_stub.NetworkApiStub(mock_state='routers')

  def execute(self, num_retries=0):
    raise ValueError(
        f"can't call this method here (mock_state: {self.mock_state}")
