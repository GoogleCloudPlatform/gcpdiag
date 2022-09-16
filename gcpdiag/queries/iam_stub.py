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
import re
from typing import Optional

import googleapiclient.errors
import httplib2

from gcpdiag.queries import apis_stub

# pylint: disable=unused-argument
# pylint: disable=invalid-name

PREFIX_GKE1 = pathlib.Path(__file__).parents[2] / 'test-data/gke1/json-dumps'


class IamApiStub:
  """Mock object to simulate IAM API calls."""

  # example API call: iam_api.projects().roles().list().execute()

  def __init__(self,
               api_project_id: Optional[str] = None,
               mock_state='init',
               argument=None):
    # project_id cannot be easily extracted from a service account name and can
    # contain a project id / number in different places, for example:
    #   SERVICE_ACCOUNT_NAME@PROJECT_ID.iam.gserviceaccount.com
    #   PROJECT_NUMBER-compute@developer.gserviceaccount.com
    #   service-PROJECT_NUMBER@compute-system.iam.gserviceaccount.com
    #   PROJECT_NUMBER@cloudservices.gserviceaccount.com
    # keeping api_project_id to map those requests to the correct json dumps
    self.api_project_id = api_project_id
    self.mock_state = mock_state
    self.project_id = None
    self.argument = argument

  def new_batch_http_request(self, callback=None):
    if callback:
      return apis_stub.BatchRequestStub(callback)
    else:
      return apis_stub.BatchRequestStub()

  def projects(self):
    return IamApiStub(self.api_project_id, 'projects')

  def serviceAccounts(self):
    return IamApiStub(self.api_project_id, 'serviceaccounts')

  def get(self, name):
    if self.mock_state == 'serviceaccounts':
      m = re.match(r'projects/[^/]+/serviceAccounts/(.*)', name)
      return IamApiStub(self.api_project_id, 'serviceaccounts_get', m.group(1))
    elif self.mock_state == 'roles':
      # roles.get is only used for predefined roles, skip extracting project_id
      return IamApiStub(self.api_project_id, 'roles_get', name)
    else:
      raise ValueError("can't call this method here (mock_state: %s)" %
                       self.mock_state)

  def getIamPolicy(self, resource):
    if self.mock_state == 'serviceaccounts':
      m = re.match(r'projects/[^/]+/serviceAccounts/(.*)', resource)
      return IamApiStub(self.api_project_id, 'serviceaccounts_getIamPolicy',
                        m.group(1))
    else:
      raise ValueError("can't call this method here (mock_state: %s)" %
                       self.mock_state)

  def roles(self):
    if self.mock_state == 'init':
      return IamApiStub(self.api_project_id, 'roles')
    elif self.mock_state == 'projects':
      return IamApiStub(self.api_project_id, 'project_roles')
    else:
      raise ValueError("can't call this method here (mock_state: %s)" %
                       self.mock_state)

  def list(self, parent, view):
    self.list_page = 1
    m = re.match(r'projects/([^/]+)', parent)
    if m:
      self.project_id = m.group(1)
    return self

  def list_next(self, previous_request, previous_response):
    self.list_page += 1
    if self.list_page >= 3:
      return None
    return self

  @property
  def uri(self):
    return f'https://iam.googleapis.com/v1/projects/-/serviceAccounts/{self.argument}?alt=json'

  def execute(self, num_retries=0):
    if self.mock_state == 'roles':
      # Predefined roles don't depend on a project, always using dump in `gke1`
      json_dir = PREFIX_GKE1
    elif self.project_id:
      json_dir = apis_stub.get_json_dir(self.project_id)
    elif self.api_project_id:
      json_dir = apis_stub.get_json_dir(self.api_project_id)
    else:
      json_dir = PREFIX_GKE1

    if self.mock_state == 'serviceaccounts_get':
      service_accounts_filename = json_dir / 'iam-service-accounts.json'
      with open(service_accounts_filename, encoding='utf-8') as json_file:
        service_accounts_data = json.load(json_file)
        service_accounts = {
            sa['email']: sa for sa in service_accounts_data['accounts']
        }
        if self.argument in service_accounts:
          return service_accounts[self.argument]
        else:
          raise googleapiclient.errors.HttpError(
              httplib2.Response({'status': 404}), b'not found')
    elif self.mock_state == 'serviceaccounts_getIamPolicy':
      json_filename = json_dir / 'iam-service-account-policy.json'
      with open(json_filename, encoding='utf-8') as json_file:
        return json.load(json_file)
    elif self.mock_state == 'roles_get':
      json_filename = json_dir / 'iam-roles-get.json'
      with open(json_filename, encoding='utf-8') as json_file:
        roles_data = json.load(json_file)
        roles = {role['name']: role for role in roles_data['roles']}
        if self.argument in roles:
          return roles[self.argument]
        else:
          raise googleapiclient.errors.HttpError(
              httplib2.Response({'status': 404}), b'not found')
    else:
      if self.mock_state == 'roles':
        json_filename = json_dir / f'iam-roles-predefined-{self.list_page}.json.gz'
      elif self.mock_state == 'project_roles':
        json_filename = json_dir / 'iam-roles-custom.json'
      else:
        raise ValueError("can't call this method here (mock_state: %s)" %
                         self.mock_state)

      if json_filename.suffix == '.gz':
        with gzip.open(json_filename) as json_file:
          return json.load(json_file)
      else:
        with open(json_filename, encoding='utf-8') as json_file:
          return json.load(json_file)
