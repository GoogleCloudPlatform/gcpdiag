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
"""Test code in crm.py."""

import unittest
from unittest import mock

from gcpdiag.queries import apis_stub, orgpolicy

DUMMY_PROJECT_ID = 'gcpdiag-fw-policy-aaaa'


@mock.patch('gcpdiag.queries.apis.get_api', new=apis_stub.get_api_stub)
class Test(unittest.TestCase):
  """Test project.py"""

  def test_get_effective_org_policy(self):
    p = orgpolicy.get_effective_org_policy(
        DUMMY_PROJECT_ID, 'constraints/compute.disableSerialPortAccess')
    assert p.is_enforced()

    p = orgpolicy.get_effective_org_policy(
        DUMMY_PROJECT_ID, 'constraints/compute.requireOsLogin')
    assert not p.is_enforced()

  def test_get_all_project_org_policies(self):
    policies = orgpolicy.get_all_project_org_policies(DUMMY_PROJECT_ID)
    assert len(policies) == 2
    assert isinstance(
        policies['constraints/cloudbuild.allowedWorkerPools'],
        orgpolicy.ListPolicyConstraint,
    )
    assert isinstance(
        policies['constraints/compute.skipDefaultNetworkCreation'],
        orgpolicy.BooleanPolicyConstraint,
    )
    assert policies['constraints/cloudbuild.allowedWorkerPools'].allowed_values(
    ) == ['projects/12340004/locations/us-central1/workerPools/test-pool']
