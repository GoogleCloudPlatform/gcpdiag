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

from unittest import mock

from gcpdiag import models
from gcpdiag.queries import apis_stub, looker

DUMMY_PROJECT_NAME = 'gcpdiag-looker1-aaaa'
DUMMY_I_NAME = f'projects/{DUMMY_PROJECT_NAME}/locations/us-central1/instances/gcpdiag-test-01'

# pylint: disable=consider-iterating-dictionary


@mock.patch('gcpdiag.queries.apis.get_api', new=apis_stub.get_api_stub)
class TestInstance:
  """Test Looker.Instances."""

  def test_get_instances_by_project(self):
    """get_instances returns the number of instances in the given project."""
    context = models.Context(project_id=DUMMY_PROJECT_NAME)
    instances = looker.get_only_instances(context)
    assert DUMMY_I_NAME in instances and len(instances) >= 1
