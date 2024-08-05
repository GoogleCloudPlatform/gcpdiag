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
"""Recommender Stub API

Instead of doing real API calls, we return test JSON data.
"""
from gcpdiag.queries import apis_stub, billing_stub

# pylint: disable=unused-argument
# pylint: disable=invalid-name


class RecommenderApiStub:
  """Mock object to simulate recommender cost insights"""

  def billingAccounts(self):
    return billing_stub.RecommenderBillingApiStub()

  def projects(self):
    return self

  def locations(self):
    return self

  def insightTypes(self):
    return self

  def insights(self):
    return self

  def list(self, parent):
    parent_split = parent.split('/')
    project, insight_type = parent_split[1], parent_split[-1]
    if insight_type == 'google.networkanalyzer.networkservices.loadBalancerInsight':
      return apis_stub.RestCallStub(project, 'lb-insights')

  def list_next(self, previous_request, previous_response):
    return None
