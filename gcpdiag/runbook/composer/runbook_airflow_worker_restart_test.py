# Copyright 2026 Google LLC
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
"""Test class for composer/Runbook_airflow_worker_restart"""

from gcpdiag import config
from gcpdiag.runbook import composer, snapshot_test_base


class Test(snapshot_test_base.RulesSnapshotTestBase):
  rule_pkg = composer
  runbook_name = 'composer/runbook_airflow_worker_restart'
  project_id = 'gcpdiag-composer1-aaaa'
  config.init({'auto': True, 'interface': 'cli'}, project_id)

  rule_parameters = [
    {
      'project_id': 'gcpdiag-composer1-aaaa',
      'name': 'env2',
      'start_time': '2026-06-18T15:07:02.016586',
      'end_time': '2026-06-18T18:07:02.016586',
    }
  ]
