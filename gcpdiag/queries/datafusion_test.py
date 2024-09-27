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
"""Test code in datafusion.py."""

from unittest import mock

from gcpdiag import models
from gcpdiag.queries import apis_stub, datafusion, web_stub
from gcpdiag.queries.generic_api.api_build import generic_api_stub

DUMMY_REGION = 'us-central1'
DUMMY_PROJECT_NAME = 'gcpdiag-datafusion1-aaaa'
DUMMY_PROJECT_NR = '12340010'
DUMMY_DEFAULT_NAME = 'default'
DUMMY_INSTANCE1_NAME = 'my-instance'
DUMMY_INSTANCE1_LABELS = {'gcpdiag': 'test'}

GCE_SERVICE_ACCOUNT = '12340010-compute@developer.gserviceaccount.com'
ENV_SERVICE_ACCOUNT = f'env2sa@{DUMMY_PROJECT_NAME}.iam.gserviceaccount.com'
NUMBER_OF_INSTANCES_IN_DATAFUSION_JSON_DUMP_FILE = 1
SUPPORTED_VERSIONS_DICT = {
    '6.9': '2025-03-31',
    '6.8': '2024-08-31',
    '6.7': '2023-02-28',
    '6.6': '2023-10-31',
    '6.5': '2023-05-31',
    '6.4': '2022-11-30',
    '6.3': '2022-07-31',
    '6.2': '2022-03-31',
    '6.1': '2021-06-30',
}
DATAFUSION_DATAPROC_VERSIONS_DICT = {
    '6.7': ['1.3'],
    '6.6': ['2.0', '1.3'],
    '6.5': ['2.0', '1.3'],
    '6.4': ['2.0', '1.3'],
    '6.3': ['1.3'],
    '6.2': ['1.3'],
    '6.1': ['1.3'],
}


@mock.patch('gcpdiag.queries.apis.get_api', new=apis_stub.get_api_stub)
class TestDataFusion:
  """Test Data Fusion"""

  def test_get_instances(self):
    context = models.Context(project_id=DUMMY_PROJECT_NAME)
    instances = datafusion.get_instances(context)
    assert len(instances) == NUMBER_OF_INSTANCES_IN_DATAFUSION_JSON_DUMP_FILE

  def test_running(self):
    context = models.Context(project_id=DUMMY_PROJECT_NAME)
    instances = datafusion.get_instances(context)
    assert (DUMMY_INSTANCE1_NAME,
            True) in [(i.name, i.is_running) for k, i in instances.items()]

  def test_is_private_ip(self):
    context = models.Context(project_id=DUMMY_PROJECT_NAME)
    instances = datafusion.get_instances(context)
    assert (DUMMY_INSTANCE1_NAME,
            True) in [(i.name, i.is_private) for k, i in instances.items()]


@mock.patch('gcpdiag.queries.web.get', new=web_stub.get)
class TestExtractVersionPolicyDict:
  """Test html content."""

  def test_extract_support_datafusion_version(self):
    response_dict = datafusion.extract_support_datafusion_version()
    assert response_dict == SUPPORTED_VERSIONS_DICT

  def test_extract_datafusion_dataproc_version(self):
    response_dict = datafusion.extract_datafusion_dataproc_version()
    assert response_dict == DATAFUSION_DATAPROC_VERSIONS_DICT


@mock.patch('gcpdiag.queries.apis.get_api', new=apis_stub.get_api_stub)
@mock.patch('gcpdiag.queries.generic_api.api_build.get_generic.get_generic_api',
            new=generic_api_stub.get_generic_api_stub)
class TestComputeProfile:
  """Test Compute Profile"""

  def test_get_instance_system_compute_profile(self):
    context = models.Context(project_id=DUMMY_PROJECT_NAME)
    instances = datafusion.get_instances(context)
    instance = list(instances.values())[0]
    profiles = datafusion.get_instance_system_compute_profile(context, instance)
    assert len(profiles) == 2

  def test_get_instance_user_compute_profile(self):
    context = models.Context(project_id=DUMMY_PROJECT_NAME)
    instances = datafusion.get_instances(context)
    instance = list(instances.values())[0]
    profiles = datafusion.get_instance_user_compute_profile(context, instance)
    assert len(profiles) == 1


@mock.patch('gcpdiag.queries.apis.get_api', new=apis_stub.get_api_stub)
@mock.patch('gcpdiag.queries.generic_api.api_build.get_generic.get_generic_api',
            new=generic_api_stub.get_generic_api_stub)
class TestPreferences:
  """Test datafusion cdap preferences"""

  def test_get_system_preferences(self):
    context = models.Context(project_id=DUMMY_PROJECT_NAME)
    instances = datafusion.get_instances(context)
    instance = list(instances.values())[0]
    preference = datafusion.get_system_preferences(context, instance)
    assert preference.image_version == '2.1'

  def test_get_application_preferences(self):
    context = models.Context(project_id=DUMMY_PROJECT_NAME)
    instances = datafusion.get_instances(context)
    instance = list(instances.values())[0]
    preferences = datafusion.get_application_preferences(context, instance)
    assert '2.2' in [(i.image_version) for k, i in preferences.items()]

  def test_get_namespace_preferences(self):
    context = models.Context(project_id=DUMMY_PROJECT_NAME)
    instances = datafusion.get_instances(context)
    instance = list(instances.values())[0]
    preferences = datafusion.get_namespace_preferences(context, instance)
    assert '2.1' in [(i.image_version) for k, i in preferences.items()]
