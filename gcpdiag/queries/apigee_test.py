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
DUMMY_APIGEE_ORG_RUNTIME_TYPE = 'CLOUD'
DUMMY_APIGEE_NETWORK_NAME = 'default'
DUMMY_APIGEE_ENVGROUP_NAME = 'gcpdiag-demo-envgroup'
DUMMY_APIGEE_ENVGROUP_FULL_PATH = \
        f'organizations/{DUMMY_APIGEE_ORG_NAME}/envgroups/{DUMMY_APIGEE_ENVGROUP_NAME}'
DUMMY_APIGEE_ENVGROUP_HOST_NAMES = ['gcpdiag.apigee.example.com']
DUMMY_APIGEE_ENVGROUP1_ATTACHMENTS_ENV = 'gcpdiag-demo-env-1'
DUMMY_APIGEE_ENVGROUP1_NAME = 'gcpdiag-demo-envgroup-1'
DUMMY_APIGEE_ENVGROUP1_FULL_PATH = \
       f'organizations/{DUMMY_APIGEE_ORG_NAME}/envgroups/{DUMMY_APIGEE_ENVGROUP1_NAME}'
DUMMY_APIGEE_INSTANCE1_NAME = 'gcpdiag-apigee1-inst1-aaaa'
DUMMY_APIGEE_INSTANCE1_FULL_PATH = \
        f'organizations/{DUMMY_APIGEE_ORG_NAME}/instances/{DUMMY_APIGEE_INSTANCE1_NAME}'
DUMMY_APIGEE_INSTANCE1_ATTACHMENTS_ENV = 'gcpdiag-demo-env'
DUMMY_APIGEE_NETWORK_BRIDGE_INSTANCE_GROUP1_NAME = 'mig-bridge-manager-us-central1'


@mock.patch('gcpdiag.queries.apis.get_api', new=apis_stub.get_api_stub)
class TestOrganization:
  """Test apigee.Organization."""

  def test_get_org(self):
    """ get_org returns the right apigee organization by project name """
    context = models.Context(project_id=DUMMY_PROJECT_NAME)
    apigee_org = apigee.get_org(context=context)

    assert apigee_org.name == DUMMY_APIGEE_ORG_NAME
    assert apigee_org.runtime_type == DUMMY_APIGEE_ORG_RUNTIME_TYPE
    assert apigee_org.network.project_id == DUMMY_PROJECT_NAME
    assert apigee_org.network.name == DUMMY_APIGEE_NETWORK_NAME

    apigee_envs = [e.name for e in apigee_org.environments]
    assert DUMMY_APIGEE_ENVGROUP1_ATTACHMENTS_ENV in apigee_envs
    assert DUMMY_APIGEE_INSTANCE1_ATTACHMENTS_ENV in apigee_envs

  def test_get_envgroups(self):
    context = models.Context(project_id=DUMMY_PROJECT_NAME)
    apigee_org = apigee.get_org(context=context)
    apigee_envgroups = apigee.get_envgroups(apigee_org)
    assert len(apigee_envgroups) == 2
    assert DUMMY_APIGEE_ENVGROUP_NAME in apigee_envgroups

    e = apigee_envgroups[DUMMY_APIGEE_ENVGROUP_NAME]
    assert e.full_path == DUMMY_APIGEE_ENVGROUP_FULL_PATH
    assert e.host_names == DUMMY_APIGEE_ENVGROUP_HOST_NAMES

  def test_get_envgroups_attachments(self):
    apigee_envgroups_attachments = apigee.get_envgroups_attachments(
        envgroup_name=DUMMY_APIGEE_ENVGROUP1_FULL_PATH)
    assert DUMMY_APIGEE_ENVGROUP1_ATTACHMENTS_ENV in apigee_envgroups_attachments

  def test_get_instances(self):
    context = models.Context(project_id=DUMMY_PROJECT_NAME)
    apigee_org = apigee.get_org(context=context)
    apigee_instances = apigee.get_instances(apigee_org)

    assert len(apigee_instances) == 1
    assert DUMMY_APIGEE_INSTANCE1_NAME in apigee_instances

    i = apigee_instances[DUMMY_APIGEE_INSTANCE1_NAME]
    assert i.full_path == DUMMY_APIGEE_INSTANCE1_FULL_PATH

  def test_get_instances_attachments(self):
    apigee_instances_attachments = apigee.get_instances_attachments(
        instance_name=DUMMY_APIGEE_INSTANCE1_FULL_PATH)
    assert DUMMY_APIGEE_INSTANCE1_ATTACHMENTS_ENV in apigee_instances_attachments

  def test_get_network_bridge_instance_groups(self):
    apigee_network_bridge_migs = apigee.get_network_bridge_instance_groups(
        project_id=DUMMY_PROJECT_NAME)

    assert len(apigee_network_bridge_migs) == 1
    assert apigee_network_bridge_migs[
        0].name == DUMMY_APIGEE_NETWORK_BRIDGE_INSTANCE_GROUP1_NAME
