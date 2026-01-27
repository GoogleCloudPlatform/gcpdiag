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
"""Test class for vpn/Vpn_tunnel_check"""

from gcpdiag import config
from gcpdiag.runbook import snapshot_test_base, vpn


class Test(snapshot_test_base.RulesSnapshotTestBase):
  rule_pkg = vpn
  runbook_name = 'vpn/vpn_tunnel_check'
  project_id = 'gcpdiag-vpn1-aaaa'
  config.init({'auto': True, 'interface': 'cli'}, project_id)
  rule_parameters = [{
      'project_id': 'gcpdiag-vpn1-aaaa',
      'region': 'europe-west4-a',
      'name': 'vpn-tunnel-1',
      'custom_flag': 'vpn'
  }, {
      'project_id': 'gcpdiag-vpn1-aaaa',
      'region': 'europe-west4-a',
      'name': 'vpn-tunnel-down',
      'custom_flag': 'vpn'
  }]
