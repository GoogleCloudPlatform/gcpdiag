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
import pytest

from gcpdiag.queries import apis_stub, iam


def get_cache_stub():
  """Use a temporary directory instead of the user cache for testing.
  This is used to avoid using the cached IAM roles from the disk cache."""
  return diskcache.Cache()


TEST_PROJECT_ID = 'gcpdiag-gke1-aaaa'
TEST_PROJECT_IAM_ID = 'gcpdiag-iam1-aaaa'
TEST_SERVICE_ACCOUNT = 'gke2sa@gcpdiag-gke1-aaaa.iam.gserviceaccount.com'
TEST_SERVICE_ACCOUNT_ROLE = 'projects/gcpdiag-gke1-aaaa/roles/gke2_custom_role'
TEST_SERVICE_ACCOUNT_PERMISSIONS = [
    'autoscaling.sites.writeMetrics',
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
    'storage.objects.get',
    'storage.objects.list',
]

TEST_DUMMY_SERVICE_ACCOUNT = {
    'gke2sa@gcpdiag-gke1-aaaa.iam.gserviceaccount.com',  # custom service account
    'gcpdiag-gke1-aaaa@appspot.gserviceaccount.com',  # GAE Default SA
    '12340002-compute@developer.gserviceaccount.com',  # GCE Default SA
    # Sample Service Agent
    'service-12340002@gcp-sa-aiplatform-cc.iam.gserviceaccount.com',
    'p12340002-123a@gcp-sa-cloud-sql.iam.gserviceaccount.com'
}


@mock.patch('gcpdiag.queries.apis.get_api', new=apis_stub.get_api_stub)
@mock.patch('gcpdiag.caching.get_cache', new=get_cache_stub)
class TestProjectPolicy:
  """Test gke.ProjectPolicy"""

  def test_get_member_permissions(self):
    policy = iam.get_project_policy(TEST_PROJECT_ID)
    assert policy.get_member_permissions(
        f'serviceAccount:{TEST_SERVICE_ACCOUNT}'
    ) == TEST_SERVICE_ACCOUNT_PERMISSIONS

  def test_has_permission(self):
    policy = iam.get_project_policy(TEST_PROJECT_ID)
    assert policy.has_permission(f'serviceAccount:{TEST_SERVICE_ACCOUNT}',
                                 'monitoring.groups.get')
    assert not policy.has_permission(f'serviceAccount:{TEST_SERVICE_ACCOUNT}',
                                     'monitoring.groups.create')

  # pylint: disable=protected-access
  def test_has_role(self):
    policy = iam.get_project_policy(TEST_PROJECT_ID)
    assert policy._has_role(f'serviceAccount:{TEST_SERVICE_ACCOUNT}',
                            TEST_SERVICE_ACCOUNT_ROLE)
    assert not policy._has_role(f'serviceAccount:{TEST_SERVICE_ACCOUNT}',
                                'roles/container.nodeServiceAgent')

  def test_has_role_permissions(self):
    policy = iam.get_project_policy(TEST_PROJECT_ID)
    assert policy.has_role_permissions(f'serviceAccount:{TEST_SERVICE_ACCOUNT}',
                                       'roles/monitoring.viewer')
    assert not policy.has_role_permissions(
        f'serviceAccount:{TEST_SERVICE_ACCOUNT}', 'roles/monitoring.editor')

  def test_missing_role(self):
    with pytest.raises(iam.RoleNotFoundError):
      policy = iam.get_project_policy(TEST_PROJECT_ID)
      policy.has_role_permissions(f'serviceAccount:{TEST_SERVICE_ACCOUNT}',
                                  'roles/non-existing-role')

  def test_internal_role(self):
    policy = iam.get_project_policy(TEST_PROJECT_ID)
    policy.has_role_permissions(f'serviceAccount:{TEST_SERVICE_ACCOUNT}',
                                'roles/container.nodeServiceAgent')

  def test_is_service_acccount_existing(self):
    assert iam.is_service_account_existing(TEST_SERVICE_ACCOUNT,
                                           TEST_PROJECT_ID)

  def test_is_service_acccount_existing_inexisting(self):
    assert not iam.is_service_account_existing('foobar@example.com',
                                               TEST_PROJECT_ID)

  def test_is_service_acccount_enabled(self):
    assert iam.is_service_account_enabled(TEST_SERVICE_ACCOUNT, TEST_PROJECT_ID)

  def test_service_account_policy(self):
    policy = iam.get_service_account_iam_policy(TEST_PROJECT_ID,
                                                TEST_SERVICE_ACCOUNT)
    assert policy.has_role_permissions(f'serviceAccount:{TEST_SERVICE_ACCOUNT}',
                                       'roles/iam.serviceAccountUser')
    assert not policy.has_role_permissions(
        f'serviceAccount:{TEST_SERVICE_ACCOUNT}', 'roles/monitoring.editor')

  def test_project_id_extraction_from_service_account(self):
    for sa in TEST_DUMMY_SERVICE_ACCOUNT:
      extracted_project_id = iam._extract_project_id(sa)
      assert TEST_PROJECT_ID == extracted_project_id

    # Test exceptional case which should return '-' wildcard
    wild_card = iam._extract_project_id('random-sa@fake-sa-iam-gservice.com')
    assert wild_card == '-'

  def test_service_account_list(self):
    service_accounts = iam.get_service_account_list(TEST_PROJECT_IAM_ID)
    assert len(service_accounts) > 1

    for account in service_accounts:
      if account.unique_id == '102417873155869406705':
        assert (account.email ==
                'demo2sa@gcpdiag-iam1-aaaa.iam.gserviceaccount.com')
      if account.unique_id == '112819826788395589395':
        assert account.email == '12340002-compute@developer.gserviceaccount.com'
      if account.unique_id == '106302102062593675693':
        assert (
            account.email == 'demo1@gcpdiag-iam1-aaaa.iam.gserviceaccount.com')
      if account.unique_id == '104735732736559639086':
        assert (
            account.email == 'demo3@gcpdiag-iam1-aaaa.iam.gserviceaccount.com')
