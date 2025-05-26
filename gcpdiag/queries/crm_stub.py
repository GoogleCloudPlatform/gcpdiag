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

import re

from gcpdiag.queries import apis_stub

# pylint: disable=unused-argument

DUMMY_PROJECT_ID = 'gcpdiag-billing1-aaaa'


class CrmApiStub:
  """Mock object to simulate CRM API calls."""

  # example API call:
  # crm_api.projects().getIamPolicy(resource=self._project_id).execute()

  def new_batch_http_request(self):
    return apis_stub.BatchRequestStub()

  def projects(self):
    return self

  # pylint: disable=redefined-builtin
  def list(self, parent=None, page_token=None, filter=None):
    if not parent:
      return apis_stub.RestCallStub(DUMMY_PROJECT_ID, 'projects')

  def list_next(self, previous_request, previous_response):
    return None

  def search(self, query=None):
    return apis_stub.RestCallStub(DUMMY_PROJECT_ID, 'projects')

  def search_next(self, previous_request, previous_response):
    return None

  # pylint: disable=invalid-name
  def get(self, project_id=None, name=None):
    if not project_id and name is not None:
      m = re.match(r'projects/(.*)', name)
      project_id = m.group(1)
    return apis_stub.RestCallStub(project_id, 'project')

  # pylint: disable=invalid-name
  def getIamPolicy(self, resource):
    m = re.match(r'projects/(.*)', resource)
    project_id = m.group(1)
    return apis_stub.RestCallStub(project_id, 'iam-policy')

  # pylint: disable=invalid-name
  def getEffectiveOrgPolicy(self, resource, body):
    m = re.match(r'projects/([^/]+)', resource)
    if not m:
      raise ValueError(
          'only projects are supported for getEffectiveOrgPolicy stub')
    project_id = m.group(1)
    if 'constraint' not in body:
      raise ValueError('constraint not defined')
    m = re.match(r'(customConstraints|constraints)/([^/]+)', body['constraint'])
    if not m:
      raise ValueError(
          f"constraint doesn\'t start with constraints/: {body['constraint']}")
    return apis_stub.RestCallStub(project_id, f'org-constraint-{m.group(2)}')

  def listOrgPolicies(self, resource):
    m = re.match(r'projects/([^/]+)', resource)
    if not m:
      raise ValueError('only projects are supported for listOrgPolicies stub')
    project_id = m.group(1)
    return apis_stub.RestCallStub(project_id, 'org-policies')

  def listOrgPolicies_next(self, previous_request, previous_response):
    if isinstance(previous_response,
                  dict) and previous_response.get('nextPageToken'):
      return apis_stub.RestCallStub(
          project_id=previous_request.project_id,
          json_basename=previous_request.json_basename,
          page=previous_request.page + 1,
      )
    else:
      return None

  def listAvailableOrgPolicyConstraints(self, resource):
    m = re.match(r'projects/([^/]+)', resource)
    if not m:
      raise ValueError(
          'only projects are supported for listAvailableOrgPolicyConstraints'
          ' stub')
    project_id = m.group(1)
    return apis_stub.RestCallStub(project_id, 'org-constraints')

  def listAvailableOrgPolicyConstraints_next(self, previous_request,
                                             previous_response):
    if isinstance(previous_response,
                  dict) and previous_response.get('nextPageToken'):
      return apis_stub.RestCallStub(
          project_id=previous_request.project_id,
          json_basename=previous_request.json_basename,
          page=previous_request.page + 1,
      )
    else:
      return None
