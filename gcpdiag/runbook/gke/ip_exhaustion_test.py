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
"""Test class for gke/IpExhaustionIssues"""

from gcpdiag import config
from gcpdiag.runbook import gke, snapshot_test_base


class Test(snapshot_test_base.RulesSnapshotTestBase):
  rule_pkg = gke
  runbook_name = 'gke/ip-exhaustion'
  project_id = 'gcpdiag-gke3-runbook'
  config.init({'auto': True, 'interface': 'cli'}, project_id)

  rule_parameters = [{
      'name': 'cluster-1',
      'location': 'us-central1-c',
      'start_time_utc': '2024-06-30T01:00:00Z',
      'end_time_utc': '2024-06-30T23:00:00Z'
  }]
