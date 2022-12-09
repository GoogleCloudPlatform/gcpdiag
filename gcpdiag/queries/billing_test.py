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
"""Test code in billing.py."""

from unittest import mock

from gcpdiag import models
from gcpdiag.queries import apis_stub, billing

DUMMY_PROJECT_ID = 'gcpdiag-billing1-aaaa'
DUMMY_BILLING_ACCOUNT_NAME = 'Cloud Billing Support billing account'
DUMMY_BILLING_ACCOUNT_IS_MASTER = False
DUMMY_BILLING_ACCOUNT_IS_OPEN = True
DUMMY_BILLING_ACCOUNT_HAS_PROJECTS = True
DUMMY_NUMBER_ALL_BILLING_ACCOUNTS = 4
DUMMY_NUMBER_ALL_PROJECTS = 3
DUMMY_PROJECT_BILLING_ENABLED = True
DUMMY_PROJECT_NAME = 'projects/gcpdiag-billing1-aaaa/billingInfo'
DUMMY_PROJECT_BILLING_ACCOUNT_NAME = 'billingAccounts/005E32-00FAKE-123456'
DUMMY_COST_INSIGHT_IS_ANOMALY = True
DUMMY_COST_INSIGHT_FORCASTED_UNITS = '80'
DUMMY_COST_INSIGHT_FORCASTED_CURRENCY = 'USD'
DUMMY_COST_INSIGHT_ACTUAL_UNITS = '16'
DUMMY_COST_INSIGHT_ACTUAL_CURRENCY = 'USD'
DUMMY_COST_INSIGHT_ANOMALY_TYPE = 'Below'


@mock.patch('gcpdiag.queries.apis.get_api', new=apis_stub.get_api_stub)
class TestBilling:
  """Test Billing queries"""

  def test_get_billing_account(self):
    context = models.Context(project_id=DUMMY_PROJECT_ID)
    billing_account = billing.get_billing_account(context.project_id)

    assert billing_account.display_name == DUMMY_BILLING_ACCOUNT_NAME
    assert billing_account.is_open() == DUMMY_BILLING_ACCOUNT_IS_OPEN
    assert billing_account.is_master() == DUMMY_BILLING_ACCOUNT_IS_MASTER
    assert (len(billing_account.list_projects()) >
            0) == DUMMY_BILLING_ACCOUNT_HAS_PROJECTS

  def test_get_all_billing_accounts(self):
    context = models.Context(project_id=DUMMY_PROJECT_ID)
    billing_accounts = billing.get_all_billing_accounts(context.project_id)

    assert len(billing_accounts) == DUMMY_NUMBER_ALL_BILLING_ACCOUNTS
    assert billing_accounts[1].display_name == DUMMY_BILLING_ACCOUNT_NAME

  def test_get_all_projects_in_billing_account(self):
    context = models.Context(project_id=DUMMY_PROJECT_ID)
    billing_account = billing.get_billing_account(context.project_id)
    projects = billing.get_all_projects_in_billing_account(billing_account.name)

    assert len(projects) == DUMMY_NUMBER_ALL_PROJECTS
    assert projects[-1].project_id == DUMMY_PROJECT_ID

  def test_get_billing_info(self):
    context = models.Context(project_id=DUMMY_PROJECT_ID)
    project_billing_info = billing.ProjectBillingInfo(
        context.project_id, billing.get_billing_info(context.project_id))

    assert project_billing_info.billing_account_name == DUMMY_PROJECT_BILLING_ACCOUNT_NAME
    assert project_billing_info.name == DUMMY_PROJECT_NAME
    assert project_billing_info.is_billing_enabled(
    ) == DUMMY_PROJECT_BILLING_ENABLED

  def test_get_cost_insights_for_a_project(self):
    context = models.Context(project_id=DUMMY_PROJECT_ID)
    cost_insights = billing.get_cost_insights_for_a_project(context.project_id)

    assert cost_insights.is_anomaly() == DUMMY_COST_INSIGHT_IS_ANOMALY
    assert cost_insights.forecasted_units == DUMMY_COST_INSIGHT_FORCASTED_UNITS
    assert cost_insights.forecasted_currency == DUMMY_COST_INSIGHT_FORCASTED_CURRENCY
    assert cost_insights.actual_units == DUMMY_COST_INSIGHT_ACTUAL_UNITS
    assert cost_insights.actual_currency == DUMMY_COST_INSIGHT_ACTUAL_CURRENCY
    assert cost_insights.anomaly_type == DUMMY_COST_INSIGHT_ANOMALY_TYPE
