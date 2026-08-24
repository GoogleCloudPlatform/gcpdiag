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

import datetime
import ipaddress
from unittest import mock

from gcpdiag import caching, models
from gcpdiag.queries import apis_stub, cloudsql, web_stub

DUMMY_PROJECT_NAME = 'gcpdiag-cloudsql1-aaaa'
INSTANCE_IP = ipaddress.ip_address('172.17.0.3')


@mock.patch('gcpdiag.queries.apis.get_api', new=apis_stub.get_api_stub)
class TestCloudSQL:
  """Test CloudSQL"""

  def test_get_instances(self):
    context = models.Context(project_id=DUMMY_PROJECT_NAME)
    instances = cloudsql.get_instances(context)
    assert len(instances) == 2

  def test_docker_bridge_ip_addresses(self):
    context = models.Context(project_id=DUMMY_PROJECT_NAME)
    instances = cloudsql.get_instances(context)
    sql1 = next(i for i in instances if i.name == 'sql1')
    assert INSTANCE_IP in sql1.ip_addresses

  def test_get_instances_cloudsql3(self):
    context = models.Context(project_id='gcpdiag-cloudsql3-aaaa')
    instances = cloudsql.get_instances(context)
    assert len(instances) == 3

  @mock.patch('gcpdiag.queries.web.get', new=web_stub.get)
  def test_get_release_schedule(self):
    with caching.bypass_cache():
      schedule = cloudsql.get_release_schedule()
    assert schedule is not None
    assert 'MYSQL_5_7' in schedule
    assert 'POSTGRES_12' in schedule
    assert isinstance(schedule['MYSQL_5_7'], dict)
    assert schedule['MYSQL_5_7']['regular_support_end'] == datetime.date(2025, 2, 1)
    assert schedule['MYSQL_5_7']['extended_support_end'] == datetime.date(2028, 2, 1)
    assert schedule['POSTGRES_12']['regular_support_end'] == datetime.date(2025, 2, 1)
    assert schedule['POSTGRES_12']['extended_support_end'] == datetime.date(2028, 2, 1)
