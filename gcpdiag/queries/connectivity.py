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
"""Queries related to Connectivity Test."""
import time
from enum import Enum, auto
from typing import Any, Dict, List

from gcpdiag import config, models
from gcpdiag.queries import apis


class Endpoint:
  """Represents source or destination of Connectivity test

  https://cloud.google.com/network-intelligence-center/docs/connectivity-tests/reference/networkmanagement/rest/v1/projects.locations.global.connectivityTests#endpoint
  """

  def __init__(self, project_id, instance, **kwargs):
    self.project_id = project_id
    self.instance = instance
    self.network = kwargs.get('network')
    if kwargs.get('port'):
      self.port = kwargs.get('port')


class ConnectivityTest(models.Resource):
  _resource_data: dict

  def __init__(self, project_id: str, resource_id: str, resource_data: dict):
    super().__init__(project_id)
    self.resource_id = resource_id
    self._resource_data = resource_data

  @property
  def full_path(self):
    return self._resource_data.get('name')

  @property
  def result(self):
    return self._resource_data.get('reachabilityDetails', {}).get('result')

  @property
  def traces(self):
    return self._resource_data.get('reachabilityDetails', {}).get('traces', [])

  def get_single_trace_final_step(self):
    """Gets the most important test output for analysis

    Assumes that the configuration analysis only produces a single trace
    """
    final_step = self.traces[0].get('final_steps', [])
    if final_step:
      return final_step[0]
    return {}


class Result(Enum):
  """The overall result of the test's configuration analysis."""
  RESULT_UNSPECIFIED = auto()
  REACHABLE = auto()
  UNREACHABLE = auto()
  AMBIGUOUS = auto()
  UNDETERMINED = auto()


def create_connectivity_tests(
    project_id: str, test_data: List[Dict[str, Any]]) -> List[Dict[str, str]]:
  """Creates Connectivity tests from a list of test data input

  Args:
      project_id: Project ID where the connectivity tests will be created
      test_data: List of dictionaries containing the resource_id and request body
                for example:
                  test_data = {
                      'resource_id': 'resource_id'
                      'test_input': {
                        'source': source,
                        'destination': destination,
                        'protocol': protocol,
                      }
                  }

  Returns:
    A list of dict mappings containing the resource_id and operation name
    for the newly created Operation instance when a connectivity test is created.
    For example:
    operation = {
      'resource_id': 'resource_id',
      'name': 'projects/{project_id}/locations/global/operations/{operation_id}'
    }

  """
  operations = []
  api = apis.get_api('networkmanagement', 'v1', project_id)
  parent = f'projects/{project_id}/locations/global'
  for test in test_data:
    test_id = f'gcpdiag-conn-test-{test["resource_id"]}'
    request = api.projects().locations().global_().connectivityTests().create(
        parent=parent, testId=test_id, body=test['test_input'])
    response = request.execute(num_retries=config.API_RETRIES)
    operation = {
        'resource_id': test['resource_id'],
        'name': response.get('name')
    }
    operations.append(operation)
  return operations


def get_connectivity_test_results(
    project_id: str, operations: List[Dict[str,
                                           str]]) -> List[ConnectivityTest]:
  """Get results of Connectivity tests

  Args:
    project_id: Project ID containing the connectivity tests
    operations: A list of dict mappings containing the resource_id
    and operation name for the connectivity test.
    For example:
    operation = {
      'resource_id': 'resource_id',
      'name': 'projects/{project_id}/locations/global/operations/{operation_id}'
    }

  Returns:
    List of connectivity test results
  """
  connectivity_test_results = []
  api = apis.get_api('networkmanagement', 'v1', project_id)
  for operation in operations:
    request = api.projects().locations().global_().operations().get(
        name=operation['name'])
    response = request.execute(num_retries=config.API_RETRIES)

    # Wait for operation to complete
    while not response.get('done', False):
      request = api.projects().locations().global_().operations().get(
          name=operation['name'])
      response = request.execute(num_retries=config.API_RETRIES)
      time.sleep(0.5)
    connectivity_test_results.append(
        ConnectivityTest(project_id=project_id,
                         resource_id=operation['resource_id'],
                         resource_data=response.get('response', {})))
  return connectivity_test_results


def delete_connectivity_tests(project_id: str,
                              connectivity_tests: List[str]) -> None:
  # TODO: Seems like Network Managment API does not support batch requests
  """Deletes connectivity tests

  Args:
      connectivity_tests: List of Connectivity Test resource names in the form
                          projects/{projectId}/locations/global/connectivityTests/{testId}
  """
  api = apis.get_api('networkmanagement', 'v1', project_id)
  for test in connectivity_tests:
    request = api.projects().locations().global_().connectivityTests().delete(
        name=test)
    request.execute(num_retries=config.API_RETRIES)
