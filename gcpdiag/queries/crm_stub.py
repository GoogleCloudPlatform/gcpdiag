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


class CrmApiStub:
  """Mock object to simulate CRM API calls."""

  # example API call:
  # crm_api.projects().getIamPolicy(resource=self._project_id).execute()

  def __init__(self, project_id=None):
    self.project_id = project_id

  def projects(self):
    return self

  # pylint: disable=invalid-name
  def get(self, project_id=None, name=None):
    if not project_id and name is not None:
      m = re.match(r'projects/(.*)', name)
      project_id = m.group(1)
    return apis_stub.RestCallStub(project_id, 'project')

  # pylint: disable=invalid-name
  def getIamPolicy(self, resource):
    return apis_stub.RestCallStub(resource, 'iam-policy')
