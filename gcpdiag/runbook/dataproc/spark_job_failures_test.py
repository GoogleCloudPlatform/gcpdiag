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
"""Test class for dataproc/SparkJob"""

from gcpdiag import config
from gcpdiag.runbook import dataproc, snapshot_test_base


class Test(snapshot_test_base.RulesSnapshotTestBase):
  rule_pkg = dataproc
  runbook_name = 'dataproc/spark-job-failures'
  project_id = 'gcpdiag-dataproc1-aaaa'
  success_job_id = '1234567890'
  failed_job_id = '1234567891'
  config.init({'auto': True, 'interface': 'cli'}, project_id)

  rule_parameters = [
      {
          'project_id': project_id,
          'dataproc_cluster_name': 'job_failed',
          'region': 'us-central1',
          'job_id': failed_job_id,
      },
      {
          'project_id': project_id,
          'dataproc_cluster_name': 'job-not-failed',
          'region': 'us-central1',
          'job_id': success_job_id,
      },
  ]
