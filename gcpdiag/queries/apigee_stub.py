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

import re

from gcpdiag.queries import apis_stub

# pylint: disable=unused-argument

DUMMY_PROJECT_ID = 'gcpdiag-apigee1-aaaa'


class ApigeeApiStub:
  """Mock object to simulate apigee api calls."""

  def __init__(self, project_id=DUMMY_PROJECT_ID):
    self.project_id = project_id

  def organizations(self):
    return ApigeeOraganizationsApiStub()


class ApigeeOraganizationsApiStub(ApigeeApiStub):
  """Mock object to simulate apigee organizations api calls"""

  def list(self, parent):
    return apis_stub.RestCallStub(self.project_id, 'apigee-organizations')

  def get(self, name):
    return apis_stub.RestCallStub(self.project_id, 'apigee-organization')

  def envgroups(self):
    return ApigeeEnvgroupsApiStub(self.project_id)

  def instances(self):
    return ApigeeInstancesApiStub(self.project_id)


class ApigeeEnvgroupsApiStub(ApigeeApiStub):
  """Mock object to simulate apigee environment groups api calls"""

  def list(self, parent):
    return apis_stub.RestCallStub(
        self.project_id,
        'apigee-envgroups',
        default_json_basename='apigee-envgroups-empty')

  def attachments(self):
    return ApigeeEnvGroupsAttachmentsApiStub(self.project_id)

  def list_next(self, previous_request, previous_response):
    return None


class ApigeeInstancesApiStub(ApigeeApiStub):
  """Mock object to simulate apigee instances api calls"""

  def list(self, parent):
    return apis_stub.RestCallStub(
        self.project_id,
        'apigee-instances',
        default_json_basename='apigee-instances-empty')

  def attachments(self):
    return ApigeeInstancesAttachmentsApiStub(self.project_id)

  def list_next(self, previous_request, previous_response):
    return None


class ApigeeEnvGroupsAttachmentsApiStub(ApigeeApiStub):
  """Mock object to simulate apigee environment groups attachments api calls"""

  def list(self, parent):
    m = re.match(r'organizations/([^/]+)/envgroups/(.*)', parent)
    if m:
      envgroup_name = m.group(2)
      return apis_stub.RestCallStub(
          self.project_id,
          f'apigee-envgroups-{envgroup_name}-attachments',
          default_json_basename='apigee-envgroups-attachments-empty')

  def list_next(self, previous_request, previous_response):
    return None


class ApigeeInstancesAttachmentsApiStub(ApigeeApiStub):
  """Mock object to simulate apigee instances attachments api calls"""

  def list(self, parent):
    m = re.match(r'organizations/([^/]+)/instances/(.*)', parent)
    if m:
      instance_name = m.group(2)
      return apis_stub.RestCallStub(
          self.project_id,
          f'apigee-instances-{instance_name}-attachments',
          default_json_basename='apigee-instances-attachments-empty')

  def list_next(self, previous_request, previous_response):
    return None
