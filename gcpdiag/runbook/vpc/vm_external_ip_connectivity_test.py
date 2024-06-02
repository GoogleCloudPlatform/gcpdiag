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
"""Test class for vpc/Vm_external_ip_connectivity"""

from gcpdiag import config
from gcpdiag.runbook import snapshot_test_base, vpc


class Test(snapshot_test_base.RulesSnapshotTestBase):
  rule_pkg = vpc
  runbook_name = 'vpc/vm-external-ip-connectivity'
  project_id = 'gcpdiag-vpc2-runbook'
  config.init({'auto': True, 'interface': 'cli'}, project_id)

  rule_parameters = [{
      'name': 'public-linux-valid',
      'zone': 'us-central1-a',
      'dest_ip': '151.101.3.5',
      'src_nic': 'nic0',
      'dest_port': '443'
  }, {
      'name': 'public-linux-faulty',
      'zone': 'us-central1-a',
      'dest_ip': '151.101.3.5',
      'src_nic': 'nic0',
      'dest_port': '443'
  }]
