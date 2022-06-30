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

DUMMY_PROJECT_NAME = 'gcpdiag-composer1-aaaa'
GCE_SERVICE_ACCOUNT = '12340005-compute@developer.gserviceaccount.com'
ENV_SERVICE_ACCOUNT = f'env2sa@{DUMMY_PROJECT_NAME}.iam.gserviceaccount.com'


@mock.patch('gcpdiag.queries.apis.get_api', new=apis_stub.get_api_stub)
class TestComposer:
  """Test Composer"""

  def test_get_environments(self):
    context = models.Context(project_id=DUMMY_PROJECT_NAME)
    environments = composer.get_environments(context)
    assert len(environments) == 2

  def test_running(self):
    context = models.Context(project_id=DUMMY_PROJECT_NAME)
    environments = composer.get_environments(context)
    assert ('env1', True) in [(c.name, c.is_running) for c in environments]

  def test_service_account(self):
    context = models.Context(project_id=DUMMY_PROJECT_NAME)
    environments = composer.get_environments(context)
    assert ('env1', GCE_SERVICE_ACCOUNT) in [
        (c.name, c.service_account) for c in environments
    ]
    assert ('env2', ENV_SERVICE_ACCOUNT) in [
        (c.name, c.service_account) for c in environments
    ]

  def test_is_private_ip(self):
    context = models.Context(project_id=DUMMY_PROJECT_NAME)
    environments = composer.get_environments(context)
    assert ('env1', False) in [(c.name, c.is_private_ip()) for c in environments
                              ]
    assert ('env2', True) in [(c.name, c.is_private_ip()) for c in environments]
