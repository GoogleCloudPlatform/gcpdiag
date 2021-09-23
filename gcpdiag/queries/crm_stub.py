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
import re

from gcpdiag.queries import apis_stub

# pylint: disable=unused-argument


class CrmApiStub:
  """Mock object to simulate CRM API calls."""

  # example API call:
  # crm_api.projects().getIamPolicy(resource=self._project_id).execute()

  def __init__(self, mock_state='init', project_id=None):
    self.mock_state = mock_state
    self.project_id = project_id

  def projects(self):
    return self

  # pylint: disable=invalid-name
  def get(self, project_id=None, name=None):
    if not project_id and name is not None:
      m = re.match(r'projects/(.*)', name)
      project_id = m.group(1)
    return CrmApiStub('get_project', project_id)

  # pylint: disable=invalid-name
  def getIamPolicy(self, resource):
    return CrmApiStub(mock_state='get_iam_policy', project_id=resource)

  def execute(self, num_retries=0):
    del num_retries
    json_dir = apis_stub.get_json_dir(self.project_id)
    if self.mock_state == 'get_iam_policy':
      with open(json_dir / 'iam-policy.json') as json_file:
        return json.load(json_file)
    elif self.mock_state == 'get_project':
      with open(json_dir / 'project.json') as json_file:
        return json.load(json_file)
    else:
      raise ValueError("can't call this method here")
