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
"""Stub API calls used in billing.py for testing.

Instead of doing real API calls, we return test JSON data.
"""

from gcpdiag.queries import apis_stub

# pylint: disable=unused-argument
# pylint: disable=invalid-name

DUMMY_PROJECT_ID = 'gcpdiag-billing1-aaaa'


class BillingApiStub:
  """Mock object to simulate billing api calls."""

  def __init__(self, project_id=DUMMY_PROJECT_ID):
    self.project_id = project_id

  def projects(self):
    return ProjectBillingInfo(self.project_id)

  def billingAccounts(self):
    return BillingAccountStub(self.project_id)


class ProjectBillingInfo(BillingApiStub):
  """Mock object to simulate Project Billing Info api calls"""

  def getBillingInfo(self, name):
    return apis_stub.RestCallStub(self.project_id, 'project_billing_info')


class BillingAccountStub(BillingApiStub):
  """Mock object to simulate Billing Account api calls"""

  def get(self, name):
    return apis_stub.RestCallStub(self.project_id, 'billing_account')

  def list(self):
    return apis_stub.RestCallStub(self.project_id, 'all_billing_accounts')

  def list_next(self, previous_request, previous_response):
    return None

  def projects(self):
    return BillingAccountProjectsStub(self.project_id)


class BillingAccountProjectsStub(BillingApiStub):
  """Mock object to simulate Billing Account Projects api calls"""

  def list(self, name):
    return apis_stub.RestCallStub(self.project_id,
                                  'all_billing_account_projects')

  def list_next(self, previous_request, previous_response):
    return None


class RecommenderApiStub:
  """Mock object to simulate recommender cost insights"""

  def __init__(self, project_id=DUMMY_PROJECT_ID):
    self.project_id = project_id

  def billingAccounts(self):
    return self

  def locations(self):
    return self

  def insightTypes(self):
    return self

  def insights(self):
    return self

  def get(self, name):
    return apis_stub.RestCallStub(self.project_id, 'cost_insights')

  def list(self, parent):
    return apis_stub.RestCallStub(self.project_id, 'cost_insights')

  def list_next(self, previous_request, previous_response):
    return None
