# Copyright 2025 Google LLC
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
"""Test code in looker.py."""

import datetime
from datetime import timezone
from unittest import mock

from gcpdiag import models
from gcpdiag.queries import apis_stub, looker

DUMMY_PROJECT_NAME = 'gcpdiag-looker1-aaaa'
DUMMY_I_NAME = f'projects/{DUMMY_PROJECT_NAME}/locations/us-central1/instances/gcpdiag-test-01'
DUMMY_OP_LOCATION = ['us-central1']
DUMMY_OP_ID = 'operation-1'

# This FAKE_NOW must correspond to the DUMMY_TIMESTAMP in the stub
FAKE_NOW = datetime.datetime.now(timezone.utc)


@mock.patch('gcpdiag.queries.apis.get_api', new=apis_stub.get_api_stub)
class TestInstance:
  """Test Looker.Instances."""

  def test_get_instances_by_project(self):
    """get_instances returns the number of instances in the given project."""
    context = models.Context(project_id=DUMMY_PROJECT_NAME,
                             locations=DUMMY_OP_LOCATION)
    instances = looker.get_instances(context)
    assert DUMMY_I_NAME in instances
    assert len(instances) >= 1


@mock.patch('gcpdiag.queries.apis.get_api', new=apis_stub.get_api_stub)
class TestOperation:
  """Test gcpdiag.queries.looker for operations."""

  def test_get_operations_by_project(self):
    """Test that get_operations retrieves and structures data correctly."""
    context = models.Context(project_id=DUMMY_PROJECT_NAME,
                             locations=DUMMY_OP_LOCATION,
                             parameters={'now': FAKE_NOW})
    operations_by_location = looker.get_operations(context)
    expected_instance_name = 'gcpdiag-test-01'
    location_str = DUMMY_OP_LOCATION[0]
    assert operations_by_location, 'The returned operations dictionary is empty.'
    assert location_str in operations_by_location, (
        f"Location '{location_str}' not found as a key. "
        f'Keys: {list(operations_by_location.keys())}')
    operations_at_location = operations_by_location[location_str]
    assert operations_at_location, \
        f"No operations found for location '{location_str}'."
    assert expected_instance_name in operations_at_location, (
        f"Instance '{expected_instance_name}' not found for location "
        f"'{location_str}'. Instance keys: {list(operations_at_location.keys())}"
    )
    op_list = operations_at_location[expected_instance_name]
    assert op_list and len(op_list) >= 1, (
        f"Expected at least one operation for instance '{expected_instance_name}'."
    )
    found_operation_1 = any(op.name == DUMMY_OP_ID for op in op_list)
    assert found_operation_1, (
        f"Operation with ID '{DUMMY_OP_ID}' not found in the list for instance "
        f"'{expected_instance_name}' in location '{location_str}'.")
