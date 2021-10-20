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
"""Test code in gcf.py."""

from unittest import mock

from gcpdiag import models
from gcpdiag.queries import apis_stub, gcf

DUMMY_PROJECT_NAME = 'gcpd-gcf1-s6ew'
DUMMY_CLOUD_FUNCTION_1_NAME = f'projects/{DUMMY_PROJECT_NAME}/locations/us-central1/functions/gcf1'
DUMMY_REGION_1 = 'us-central1'


@mock.patch('gcpdiag.queries.apis.get_api', new=apis_stub.get_api_stub)
class TestGcf:
  """Test GCF"""

  def test_get_functions(self):
    context = models.Context(project_id=DUMMY_PROJECT_NAME)
    cloudfunctions = gcf.get_cloudfunctions(context=context)
    assert len(cloudfunctions) == 1
    assert DUMMY_CLOUD_FUNCTION_1_NAME in cloudfunctions
