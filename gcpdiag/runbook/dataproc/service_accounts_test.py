# Copyright 2025 Google LLC
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
"""
This test class validates the service_accounts.py runbook module.
"""

from gcpdiag import dataproc
from gcpdiag.runbook import dataproc, snapshot_test_base
from gcpdiag.runbook.dataproc import service_accounts


class TestServiceAccountRule(snapshot_test_base.RulesSnapshotTestBase):
  """Test class for the ServiceAccountRule."""
  rule_pkg = service_accounts
  project_id = 'gcpdiag-dataproc1-aaaa'

  def test_run_ok(self):
    """Test case for a correctly configured service account."""
    context = runbook.RunbookContext(
        project_id=self.project_id,
        parameters={
            'project_id': self.project_id,
            'region': 'us-central1',
            'cluster_name': 'good'
        })
    op = self.execute_rule_instance(service_accounts.ServiceAccountRule(),
                                    context)
    self.assert_rule_ok(op)

  def test_run_failed(self):
    """Test case for a service account missing the dataproc.worker role."""
    context = runbook.RunbookContext(
        project_id=self.project_id,
        parameters={
            'project_id': self.project_id,
            'region': 'us-central1',
            'cluster_name': 'bad-sa'
        })
    op = self.execute_rule_instance(service_accounts.ServiceAccountRule(),
                                    context)
    self.assert_rule_failed(op)
    self.assert_incident_short_desc(
        op, 'The cluster\'s service account is missing the "Dataproc Worker" role.'
    )
