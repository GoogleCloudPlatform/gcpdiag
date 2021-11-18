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
"""Stub API calls used in apigee.py for testing.

Instead of doing real API calls, we return test JSON data.
"""

import json
import pathlib
import re
from typing import Optional

from gcpdiag.queries import apis_stub

# pylint: disable=unused-argument

APIGEE_ORG_DIR = pathlib.Path(
    __file__).parents[2] / 'test-data/apigee1/json-dumps'


class ApigeeApiStub:
  """Mock object to simulate apigee api calls."""

  # mocked methods:
  # apigee_api.organizations().list().execute()
  # apigee_api.organizations().envgroups().list().execute()
  # apigee_api.organizations().envgroups().attachments().list().execute()

  def __init__(self,
               mock_state='init',
               organization_name=None,
               environmentgroup_name=None):
    self.mock_state = mock_state
    self.organization_name = organization_name
    self.environmentgroup_name = environmentgroup_name

  def organizations(self):
    return self

  def envgroups(self):
    return self

  def attachments(self):
    return self

  # pylint: disable=invalid-name
  def list(self, parent, pageSize: Optional[int] = None):
    if parent == 'organizations':
      return ApigeeApiStub('organizations')
    m = re.match(r'organizations/([^/]+)/envgroups/(.*)', parent)
    if m:
      org_name = m.group(1)
      envgroup_name = m.group(2)
      return ApigeeApiStub('attachments',
                           organization_name=org_name,
                           environmentgroup_name=envgroup_name)
    m = re.match(r'organizations/([^/]+)', parent)
    if m:
      org_name = m.group(1)
      return ApigeeApiStub('envgroups', organization_name=org_name)

  def execute(self, num_retries=0):
    if self.organization_name:
      json_dir = apis_stub.get_json_dir(self.organization_name)
    if self.mock_state == 'organizations':
      with open(APIGEE_ORG_DIR / 'apigee-organizations.json',
                encoding='utf-8') as json_file:
        return json.load(json_file)
    elif self.mock_state == 'envgroups':
      with open(json_dir / 'environment-groups.json',
                encoding='utf-8') as json_file:
        return json.load(json_file)
    elif self.mock_state == 'attachments' and \
              self.environmentgroup_name == 'gcpdiag-demo-envgroup-1':
      with open(json_dir / 'environment-group-attachments.json',
                encoding='utf-8') as json_file:
        return json.load(json_file)
    elif self.mock_state == 'attachments' and self.environmentgroup_name == 'gcpdiag-demo-envgroup':
      with open(json_dir / 'environment-group-empty-attachments.json', \
              encoding='utf-8') as json_file:
        return json.load(json_file)
