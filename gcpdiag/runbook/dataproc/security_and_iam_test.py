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
This test class validates the security_and_iam.py runbook module.
"""

from gcpdiag import dataproc
from gcpdiag.runbook import dataproc, snapshot_test_base
from gcpdiag.runbook.dataproc import security_and_iam


class TestIamRule(snapshot_test_base.RulesSnapshotTestBase):
  """Test class for the IamRule."""
  rule_pkg = security_and_iam
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
    op = self.execute_rule_instance(security_and_iam.IamRule(), context)
    self.assert_rule_ok(op)

  def test_run_failed(self):
    """Test case for a service account missing the dataproc.worker role."""
    context = runbook.RunbookContext(
        project_id=self.project_id,
        parameters={
            'project_id': self.project_id,
            'region': 'us-central1',
            'cluster_name': 'bad-iam'
        })
    op = self.execute_rule_instance(security_and_iam.IamRule(), context)
    self.assert_rule_failed(op)
    self.assert_incident_short_desc(
        op, 'The cluster\'s service account is missing the "Dataproc Worker" role.'
    )
