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
"""Test class for dataflow/Failed_streaming_pipeline"""

from gcpdiag import config
from gcpdiag.runbook import dataflow, snapshot_test_base


class Test(snapshot_test_base.RulesSnapshotTestBase):
  rule_pkg = dataflow
  runbook_name = 'dataflow/failed-streaming-pipeline'
  project_id = 'gcpdiag-dataflow1-aaaa'
  config.init({'auto': True, 'interface': 'cli'}, project_id)

  rule_parameters = [{
      'job_id': '2024-06-19_09_43_07-14927685200167458422',
      'job_region': 'us-central1'
  }]
