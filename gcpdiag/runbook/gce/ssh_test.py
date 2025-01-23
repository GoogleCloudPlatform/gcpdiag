# Copyright 2022 Google LLC
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
""" Generalize rule snapshot testing """
from gcpdiag import config
from gcpdiag.runbook import gce, snapshot_test_base


class Test(snapshot_test_base.RulesSnapshotTestBase):
  rule_pkg = gce
  runbook_name = 'gce/ssh'
  config.init({'auto': True, 'interface': 'cli'})

  rule_parameters = [{
      'project_id': 'gcpdiag-gce-faultyssh-runbook',
      'instance_name': 'faulty-linux-ssh',
      'zone': 'europe-west2-a',
      'principal': 'user:cannotssh@example.com',
      'proxy': 'iap',
      'access_method': 'oslogin',
      'start_time': '2025-01-23 23:30:39.144959+00:00',
      'end_time': '2025-01-23 13:30:39.144959+00:00'
  }, {
      'project_id':
          'gcpdiag-gce-faultyssh-runbook',
      'instance_name':
          'valid-linux-ssh',
      'zone':
          'europe-west2-a',
      'principal':
          'serviceAccount:canssh@gcpdiag-gce-faultyssh-runbook.iam.gserviceaccount.com',
      'proxy':
          'iap',
      'access_method':
          'oslogin',
      'start_time':
          '2025-01-23 23:30:39.144959+00:00',
      'end_time':
          '2025-01-23 13:30:39.144959+00:00'
  }, {
      'project_id': 'gcpdiag-gce-faultyssh-runbook',
      'instance_name': 'faulty-windows-ssh',
      'zone': 'europe-west2-a',
      'principal': 'user:cannot@example.com',
      'src_ip': '0.0.0.0',
      'proxy': 'iap',
      'access_method': 'oslogin',
      'posix_user': 'no_user',
      'start_time': '2025-01-23 23:30:39.144959+00:00',
      'end_time': '2025-01-23 13:30:39.144959+00:00'
  }]
