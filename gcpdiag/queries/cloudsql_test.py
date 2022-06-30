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
"""Test code in cloudsql.py."""

import ipaddress
from unittest import mock

from gcpdiag import models
from gcpdiag.queries import apis_stub, cloudsql

DUMMY_PROJECT_NAME = 'gcpdiag-cloudsql1-aaaa'
INSTANCE_IP = ipaddress.ip_address('172.17.0.3')


@mock.patch('gcpdiag.queries.apis.get_api', new=apis_stub.get_api_stub)
class TestCloudSQL:
  """Test CloudSQL"""

  def test_get_instances(self):
    context = models.Context(project_id=DUMMY_PROJECT_NAME)
    instances = cloudsql.get_instances(context)
    assert len(instances) == 1

  def test_docker_bridge_ip_addresses(self):
    context = models.Context(project_id=DUMMY_PROJECT_NAME)
    instances = cloudsql.get_instances(context)
    assert INSTANCE_IP in instances[0].ip_addresses
