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
"""Stub API calls used in iam.py for testing.

Instead of doing real API calls, we return test JSON data.
"""

import gzip
import json
import pathlib

# pylint: disable=unused-argument

PREFIX_GKE1 = pathlib.Path(__file__).parents[2] / 'test-data/gke1/json-dumps'
IAM_POLICY_JSON = PREFIX_GKE1 / 'iam-policy.json'
IAM_ROLES_PRE1_JSON = PREFIX_GKE1 / 'iam-roles-predefined-1.json.gz'
IAM_ROLES_PRE2_JSON = PREFIX_GKE1 / 'iam-roles-predefined-2.json.gz'
IAM_ROLES_CUST_JSON = PREFIX_GKE1 / 'iam-roles-custom.json'
PROJECT_JSON = PREFIX_GKE1 / 'project.json'


class IamApiStub:
  """Mock object to simulate IAM API calls."""

  # example API call: iam_api.projects().roles().list().execute()

  def __init__(self, mock_state='init'):
    self.mock_state = mock_state

  def projects(self):
    return IamApiStub('projects')

  def roles(self):
    if self.mock_state == 'init':
      return IamApiStub('roles')
    elif self.mock_state == 'projects':
      return IamApiStub('project_roles')
    else:
      raise ValueError("can't call this method here")

  def execute(self, num_retries=0):
    if self.mock_state == 'roles' and self.list_page == 1:
      iam_roles_file = IAM_ROLES_PRE1_JSON
    elif self.mock_state == 'roles' and self.list_page == 2:
      iam_roles_file = IAM_ROLES_PRE2_JSON
    elif self.mock_state == 'project_roles':
      iam_roles_file = IAM_ROLES_CUST_JSON
    else:
      raise ValueError("can't call this method here")

    if iam_roles_file.suffix == '.gz':
      with gzip.open(iam_roles_file) as json_file:
        return json.load(json_file)
    else:
      with open(iam_roles_file) as json_file:
        return json.load(json_file)

  def list(self, parent, view):
    self.list_page = 1
    return self

  def list_next(self, previous_request, previous_response):
    self.list_page += 1
    if self.list_page >= 3:
      return None
    return self


class CrmApiStub:
  """Mock object to simulate CRM API calls."""

  # example API call:
  # crm_api.projects().getIamPolicy(resource=self._project_id).execute()

  def __init__(self, mock_state='init'):
    self.mock_state = mock_state

  def projects(self):
    return self

  # pylint: disable=invalid-name
  def get(self, projectId):
    del projectId
    return CrmApiStub(mock_state='get_project')

  # pylint: disable=invalid-name
  def getIamPolicy(self, resource):
    del resource
    return CrmApiStub(mock_state='get_iam_policy')

  def execute(self, num_retries=0):
    del num_retries
    if self.mock_state == 'get_iam_policy':
      with open(IAM_POLICY_JSON) as json_file:
        return json.load(json_file)
    elif self.mock_state == 'get_project':
      with open(PROJECT_JSON) as json_file:
        return json.load(json_file)
    else:
      raise ValueError("can't call this method here")


def get_api_stub(service_name: str, version: str):
  if service_name == 'iam':
    return IamApiStub()
  elif service_name == 'cloudresourcemanager':
    return CrmApiStub()
  else:
    raise ValueError(f"I don't know how to mock {service_name}")
