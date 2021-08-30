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
"""Stub API calls used in crm.py for testing.

Instead of doing real API calls, we return test JSON data.
"""

import json
import pathlib

# pylint: disable=unused-argument

PREFIX_GKE1 = pathlib.Path(__file__).parents[2] / 'test-data/gke1/json-dumps'


class CrmApiStub:
  """Mock object to simulate CRM API calls."""

  # example API call:
  # crm_api.projects().getIamPolicy(resource=self._project_id).execute()

  def __init__(self, mock_state='init'):
    self.mock_state = mock_state

  def projects(self):
    return self

  # pylint: disable=invalid-name
  def get(self, projectId=None, name=None):
    del projectId
    del name
    return CrmApiStub(mock_state='get_project')

  # pylint: disable=invalid-name
  def getIamPolicy(self, resource):
    del resource
    return CrmApiStub(mock_state='get_iam_policy')

  def execute(self, num_retries=0):
    del num_retries
    if self.mock_state == 'get_iam_policy':
      with open(PREFIX_GKE1 / 'iam-policy.json') as json_file:
        return json.load(json_file)
    elif self.mock_state == 'get_project':
      with open(PREFIX_GKE1 / 'project.json') as json_file:
        return json.load(json_file)
    else:
      raise ValueError("can't call this method here")


def get_api_stub(service_name: str, version: str, project_id: str = None):
  del project_id
  if service_name == 'cloudresourcemanager':
    return CrmApiStub()
  else:
    raise ValueError('unsupported service: %s' % service_name)
