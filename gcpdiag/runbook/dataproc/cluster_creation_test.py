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
"""Test class for dataproc/cluster-creation."""

from gcpdiag import config
from gcpdiag.runbook import dataproc, snapshot_test_base


class Test(snapshot_test_base.RulesSnapshotTestBase):
  rule_pkg = dataproc
  runbook_name = 'dataproc/cluster-creation'
  config.init({'auto': True, 'interface': 'cli'})

  rule_parameters = [
      {
          'project_id': 'gcpdiag-dataproc1-aaaa',
          'cluster_name': 'good',
          'start_time_utc': '2024-06-18T01:00:00Z',
          'end_time_utc': '2024-06-22T01:00:00Z',
      },
      {
          'project_id': 'gcpdiag-dataproc1-aaaa',
          'cluster_name': 'good',
          'start_time_utc': '2024-06-23T01:00:00Z',
          'end_time_utc': '2024-06-24T01:00:00Z',
      },
      {
          'project_id': 'gcpdiag-dataproc1-aaaa',
          'cluster_name': 'test-deny-icmp',
          'start_time_utc': '2024-06-18T01:00:00Z',
          'end_time_utc': '2024-06-22T01:00:00Z',
      },
  ]
