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
"""Test code in iam.py."""

from unittest import mock

import diskcache

from gcp_doctor.queries import apis_stub, iam


def get_cache_stub():
  """Use a temporary directory instead of the user cache for testing.
  This is used to avoid using the cached IAM roles from the disk cache."""
  return diskcache.Cache()


TEST_PROJECT_NAME = 'gcpd-gke-1-9b90'
TEST_SERVICE_ACCOUNT = 'serviceAccount:gke2sa@gcpd-gke-1-9b90.iam.gserviceaccount.com'
TEST_SERVICE_ACCOUNT_PERMISSIONS = [
    'cloudnotifications.activities.list',
    'logging.logEntries.create',
    'monitoring.alertPolicies.get',
    'monitoring.alertPolicies.list',
    'monitoring.dashboards.get',
    'monitoring.dashboards.list',
    'monitoring.groups.get',
    'monitoring.groups.list',
    'monitoring.metricDescriptors.create',
    'monitoring.metricDescriptors.get',
    'monitoring.metricDescriptors.list',
    'monitoring.monitoredResourceDescriptors.get',
    'monitoring.monitoredResourceDescriptors.list',
    'monitoring.notificationChannelDescriptors.get',
    'monitoring.notificationChannelDescriptors.list',
    'monitoring.notificationChannels.get',
    'monitoring.notificationChannels.list',
    'monitoring.publicWidgets.get',
    'monitoring.publicWidgets.list',
    'monitoring.services.get',
    'monitoring.services.list',
    'monitoring.slos.get',
    'monitoring.slos.list',
    'monitoring.timeSeries.create',
    'monitoring.timeSeries.list',
    'monitoring.uptimeCheckConfigs.get',
    'monitoring.uptimeCheckConfigs.list',
    'opsconfigmonitoring.resourceMetadata.list',
    'stackdriver.resourceMetadata.write',
]


@mock.patch('gcp_doctor.queries.apis.get_api', new=apis_stub.get_api_stub)
@mock.patch('gcp_doctor.caching.get_cache', new=get_cache_stub)
class TestProjectPolicy:
  """Test gke.ProjectPolicy"""

  def test_get_member_permissions(self):
    policy = iam.ProjectPolicy(TEST_PROJECT_NAME)
    assert policy.get_member_permissions(
        TEST_SERVICE_ACCOUNT) == TEST_SERVICE_ACCOUNT_PERMISSIONS

  def test_has_permission(self):
    policy = iam.get_project_policy(TEST_PROJECT_NAME)
    assert policy.has_permission(TEST_SERVICE_ACCOUNT, 'monitoring.groups.get')
    assert not policy.has_permission(TEST_SERVICE_ACCOUNT,
                                     'monitoring.groups.create')

  def test_has_role_permissions(self):
    policy = iam.get_project_policy(TEST_PROJECT_NAME)
    assert policy.has_role_permissions(TEST_SERVICE_ACCOUNT,
                                       'roles/monitoring.viewer')
    assert not policy.has_role_permissions(TEST_SERVICE_ACCOUNT,
                                           'roles/monitoring.editor')
