# Copyright 2022 Google LLC
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
"""Test code in connectivity.py."""
import re
from unittest import mock

from gcpdiag import models
from gcpdiag.queries import apis_stub, connectivity

DUMMY_PROJECT_NAME = 'gcpdiag-connectivity1-aaaa'


@mock.patch('gcpdiag.queries.apis.get_api', new=apis_stub.get_api_stub)
class TestConnectivityTest:
  """Test ConnectivityTest"""

  def test_create_connectivity_test(self):
    context = models.Context(project_id=DUMMY_PROJECT_NAME)
    connectivity_test_input = []
    test_data = {
        'resource_id': 'delivered',
        'test_input': {
            'source': 'source',
            'destination': 'destination',
            'protocol': 'TCP',
        }
    }
    connectivity_test_input.append(test_data)
    connectivity_test_operations = connectivity.create_connectivity_tests(
        context.project_id, connectivity_test_input)
    assert connectivity_test_operations[0]['resource_id'] == test_data[
        'resource_id']

    match = re.search(r'projects/(.*)/locations/global/operations/(.*)',
                      connectivity_test_operations[0]['name'])
    assert match is not None

  def test_get_connectivity_test_results(self):
    context = models.Context(project_id=DUMMY_PROJECT_NAME)
    resource_id = 'delivered'
    operation_id = f'operation-gcpdiag-conn-test-{resource_id}'
    operations = []
    operation = {
        'resource_id':
            'delivered',
        'name':
            f'projects/{context.project_id}/locations/global/operations/{operation_id}'
    }
    operations.append(operation)
    results = connectivity.get_connectivity_test_results(
        context.project_id, operations)
    assert results[0].result == connectivity.Result.REACHABLE.name
