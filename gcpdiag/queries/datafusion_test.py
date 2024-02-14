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
from gcpdiag.queries import apis_stub, datafusion

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
    '6.1': '2021-06-30'
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


class TestExtractVersionPolicyDict:
  """Test Http Request and Response."""

  @mock.patch('gcpdiag.queries.datafusion.requests.get', autospec=True)
  def test_extract_support_datafusion_version(self, mock_get):

    with open(
        'test-data/datafusion1/html-content/'
        'version_support_policy.html',
        encoding='utf-8') as fh:
      mock_get.return_value.content = fh.read().encode('utf-8')
      mock_get.return_value.status_code = 200

    response_dict = datafusion.extract_support_datafusion_version()
    assert response_dict == SUPPORTED_VERSIONS_DICT
