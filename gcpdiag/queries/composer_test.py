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
"""Test code in composer.py."""

from unittest import mock

from gcpdiag import models
from gcpdiag.queries import apis_stub, composer

DUMMY_PROJECT_NAME = 'composer1'


@mock.patch('gcpdiag.queries.apis.get_api', new=apis_stub.get_api_stub)
class TestComposer:
  """Test Composer"""

  def test_get_environments(self):
    context = models.Context(project_id=DUMMY_PROJECT_NAME)
    environments = composer.get_environments(context)
    assert len(environments) == 1
    assert ('good', True) in [(c.name, c.is_running) for c in environments]
