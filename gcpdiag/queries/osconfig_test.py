# Copyright 2024 Google LLC
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
"""Test code in pubsub.py."""

from unittest import mock

from gcpdiag import models
from gcpdiag.queries import apis_stub, osconfig

DUMMY_PROJECT_NAME = 'gcpdiag-osconfig1-aaaa'
PACKAGE_NAME_LINUX = 'google-fluentd'
PACKAGE_VERSION = '1.10.1-1'
OS_SHORTNAME = 'debian'
OS_VERSION = '10'
DUMMY_LOCATION = 'us-central1-a'
DUMMY_INSTANCE_NAME = 'instance-1'
DUMMY_NON_EXISTENT_INSTANCE_NAME = 'instance-does-not-exist'


@mock.patch('gcpdiag.queries.apis.get_api', new=apis_stub.get_api_stub)
class TestOSConfig:
  """Test OSConfig"""

  def test_get_inventory(self):
    context = models.Context(project_id=DUMMY_PROJECT_NAME)
    inventory = osconfig.get_inventory(
        context=context,
        location=DUMMY_LOCATION,
        instance_name=DUMMY_INSTANCE_NAME,
    )
    assert OS_SHORTNAME == inventory.os_shortname
    assert OS_VERSION == inventory.os_version
    assert PACKAGE_NAME_LINUX in inventory.installed_packages
    assert PACKAGE_VERSION == inventory.installed_packages[PACKAGE_NAME_LINUX]

  def test_get_inventory_of_non_existent_instance(self):
    context = models.Context(project_id=DUMMY_PROJECT_NAME)
    inventory = osconfig.get_inventory(
        context=context,
        location=DUMMY_LOCATION,
        instance_name=DUMMY_NON_EXISTENT_INSTANCE_NAME,
    )
    assert inventory is None
