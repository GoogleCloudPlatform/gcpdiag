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
"""Stub API calls used in dataproc.py for testing.

Instead of doing real API calls, we return test JSON data.
"""

import json
import re

from gcpdiag.queries import apis_stub

#pylint: disable=unused-argument
#pylint: disable=invalid-name


class DataprocApiStub(apis_stub.ApiStub):
  """Mock object to simulate dataproc api calls."""

  def __init__(self, json_basename=None, project_id=None, mock_state='init'):
    self.mock_state = mock_state
    self.json_basename = json_basename
    self.project_id = project_id

  def projects(self):
    return self

  def regions(self):
    return self

  def clusters(self):
    return DataprocApiStub(mock_state='clusters')

  def autoscalingPolicies(self):
    return DataprocApiStub(mock_state='autoscalingPolicies')

  def get(self, name='', clusterName='', region='', projectId=''):
    if self.mock_state == 'autoscalingPolicies':
      m = re.match(
          r'projects/([^/]+)/regions/([^/]+)/autoscalingPolicies/([^/]+)', name)
      project_id = m.group(1)
      return apis_stub.RestCallStub(project_id, 'autoscaling-policy')
    if self.mock_state == 'clusters':
      stub = DataprocApiStub(project_id=projectId,
                             json_basename=f'dataproc-clusters-{region}',
                             mock_state='clusters')
      stub.cluster_name = clusterName
      stub.region = region
      return stub

  def list(self, projectId, region):
    if self.mock_state == 'clusters':
      return apis_stub.RestCallStub(projectId,
                                    f'dataproc-clusters-{region}',
                                    default={})
    # Implement other list mocked states here

  def execute(self, num_retries=0):
    self._maybe_raise_api_exception()
    json_dir = apis_stub.get_json_dir(self.project_id)
    with open(json_dir / f'{self.json_basename}.json',
              encoding='utf-8') as json_file:
      data = json.load(json_file)
      if self.mock_state == 'clusters':
        for cluster in data.get('clusters', []):
          if cluster['clusterName'] == self.cluster_name:
            return cluster
      return data
