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
"""Test class for dataflow/FailedBatchPipeline"""

from gcpdiag import config
from gcpdiag.runbook import dataflow, snapshot_test_base

DUMMY_PROJECT_ID = 'gcpdiag-dataflow1-aaaa'
DUMMY_JOB_ID = '2026-05-18_07_03_26-5088364741087117679'
DUMMY_REGION = 'us-central1'


class Test(snapshot_test_base.RulesSnapshotTestBase):
  rule_pkg = dataflow
  runbook_name = 'dataflow/failed-batch-pipeline'
  project_id = 'gcpdiag-dataflow1-aaaa'
  config.init({'auto': True, 'interface': 'cli'}, project_id)
  rule_parameters = [
    {'project_id': DUMMY_PROJECT_ID, 'dataflow_job_id': DUMMY_JOB_ID, 'job_region': DUMMY_REGION}
  ]
