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

from gcp_doctor.queries import crm_stub

# pylint: disable=unused-argument

PREFIX_GKE1 = pathlib.Path(__file__).parents[2] / 'test-data/gke1/json-dumps'
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


def get_api_stub(service_name: str, version: str, project_id: str = None):
  del project_id
  if service_name == 'iam':
    return IamApiStub()
  elif service_name == 'cloudresourcemanager':
    return crm_stub.CrmApiStub()
  else:
    raise ValueError(f"I don't know how to mock {service_name}")
