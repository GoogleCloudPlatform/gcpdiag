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
"""Test class for lb/latency"""

from gcpdiag import config
from gcpdiag.runbook import lb, snapshot_test_base


class Test(snapshot_test_base.RulesSnapshotTestBase):
  rule_pkg = lb
  runbook_name = 'lb/latency'
  project_id = ''
  config.init({'auto': True, 'interface': 'cli'}, project_id)

  rule_parameters = [{
      'project_id': 'gcpdiag-lb3-aaaa',
      'forwarding_rule_name': 'https-content-rule',
      'region': 'global'
  }, {
      'project_id': 'gcpdiag-lb3-aaaa',
      'forwarding_rule_name': 'https-content-rule-working',
      'region': 'global'
  }, {
      'project_id': 'gcpdiag-lb3-aaaa',
      'forwarding_rule_name': 'https-content-rule',
      'region': 'global',
      'backend_latency_threshold': '700000',
      'request_count_threshold': '700000',
      'error_rate_threshold': '50'
  }]
