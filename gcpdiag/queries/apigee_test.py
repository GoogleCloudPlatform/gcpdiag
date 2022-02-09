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
"""Test code in apigee.py."""

from unittest import mock

from gcpdiag import models
from gcpdiag.queries import apigee, apis_stub

DUMMY_PROJECT_NAME = 'gcpdiag-apigee1-aaaa'
DUMMY_APIGEE_ORG_NAME = 'gcpdiag-apigee1-aaaa'
DUMMY_APIGEE_ENVGROUP_NAME = 'gcpdiag-demo-envgroup'
DUMMY_APIGEE_ENVGROUP_FULL_PATH = \
        f'organizations/{DUMMY_APIGEE_ORG_NAME}/envgroups/{DUMMY_APIGEE_ENVGROUP_NAME}'
DUMMY_APIGEE_ENVGROUP_HOST_NAMES = ['gcpdiag.apigee.example.com']
DUMMY_APIGEE_ENVGROUP1_ATTACHMENTS_ENV = 'gcpdiag-demo-env-1'
DUMMY_APIGEE_ENVGROUP1_NAME = 'gcpdiag-demo-envgroup-1'
DUMMY_APIGEE_ENVGROUP1_FULL_PATH = \
       f'organizations/{DUMMY_APIGEE_ORG_NAME}/envgroups/{DUMMY_APIGEE_ENVGROUP1_NAME}'


@mock.patch('gcpdiag.queries.apis.get_api', new=apis_stub.get_api_stub)
class TestOrganization:
  """Test apigee.Organization."""

  def test_get_org(self):
    """ get_org returns the right apigee organization by project name """
    context = models.Context(project_id=DUMMY_PROJECT_NAME)
    apigee_org = apigee.get_org(context=context)
    assert DUMMY_APIGEE_ORG_NAME in apigee_org and len(apigee_org) == 1

  def test_get_envgroups(self):
    apigee_envgroups = apigee.get_envgroups(org_name=DUMMY_APIGEE_ORG_NAME)
    e = apigee_envgroups[DUMMY_APIGEE_ENVGROUP_NAME]
    assert len(apigee_envgroups) == 2
    assert DUMMY_APIGEE_ENVGROUP_NAME in apigee_envgroups
    assert e.full_path == DUMMY_APIGEE_ENVGROUP_FULL_PATH
    assert e.host_names == DUMMY_APIGEE_ENVGROUP_HOST_NAMES

  def test_get_envgroups_attachments(self):
    apigee_envgroups_attachments = apigee.get_envgroups_attachments(
        envgroup_name=DUMMY_APIGEE_ENVGROUP1_FULL_PATH)
    assert DUMMY_APIGEE_ENVGROUP1_ATTACHMENTS_ENV in apigee_envgroups_attachments
