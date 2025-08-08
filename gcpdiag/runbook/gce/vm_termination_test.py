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
"""Snapshot testing and unittest """
from gcpdiag import config
from gcpdiag.runbook import gce, snapshot_test_base


class Test(snapshot_test_base.RulesSnapshotTestBase):
  rule_pkg = gce
  runbook_name = 'gce/vm-termination'
  config.init({'auto': True, 'interface': 'cli'})

  rule_parameters = [{
      'project_id': 'gcpdiag-gce5-aaaa',
      'instance_name': 'start-and-stop-vm',
      'zone': 'us-central1-c',
      'start_time': '2025-03-17T00:00:00+00:00',
      'end_time': '2025-03-19T00:00:00+00:00'
  }, {
      'project_id': 'gcpdiag-gce5-aaaa',
      'instance_name': 'spot-vm-termination',
      'zone': 'us-central1-c',
      'start_time': '2025-03-17T00:00:00+00:00',
      'end_time': '2025-03-19T00:00:00+00:00'
  }, {
      'project_id': 'gcpdiag-gce5-aaaa',
      'instance_name': 'shielded-vm-integrity-failure',
      'zone': 'us-central1-c',
      'start_time': '2025-03-17T00:00:00+00:00',
      'end_time': '2025-03-19T00:00:00+00:00'
  }]
