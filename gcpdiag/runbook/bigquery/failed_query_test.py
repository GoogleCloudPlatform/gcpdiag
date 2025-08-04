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
"""Test class for the bigquery/failed-query runbook."""

from gcpdiag import config
from gcpdiag.runbook import bigquery, snapshot_test_base


class Test(snapshot_test_base.RulesSnapshotTestBase):
  """Test cases for the BigQuery Failed Query runbook."""
  rule_pkg = bigquery
  runbook_name = 'bigquery/failed-query'
  runbook_id = 'Failed Query Runbook'
  config.init({'auto': True, 'interface': 'cli'})
  rule_parameters = [
      # Test Case 1: A failed job with a known error (CSV).
      {
          'project_id': 'gcpdiag-bigquery1-aaaa',
          'bigquery_job_id': 'test_csv_error',
          'bigquery_job_region': 'us',
          'bigquery_skip_permission_check': False,
      },
      # Test Case 2: A failed job with an unknown error.
      {
          'project_id': 'gcpdiag-bigquery1-aaaa',
          'bigquery_job_id': 'test_unknown',
          'bigquery_job_region': 'us',
          'bigquery_skip_permission_check': False,
      },
      # Test Case 3: A job that completed successfully (no error).
      {
          'project_id': 'gcpdiag-bigquery1-aaaa',
          'bigquery_job_id': 'test_success',
          'bigquery_job_region': 'us',
          'bigquery_skip_permission_check': False,
      },
      # Test Case 4: A job that is still running.
      {
          'project_id': 'gcpdiag-bigquery1-aaaa',
          'bigquery_job_id': 'test_running',
          'bigquery_job_region': 'us',
          'bigquery_skip_permission_check': False,
      },
      # Test Case 5: A job ID that does not exist.
      {
          'project_id': 'gcpdiag-bigquery1-aaaa',
          'bigquery_job_id': 'test_notfound',
          'bigquery_job_region': 'us',
          'bigquery_skip_permission_check': False,
      },
      # Test Case 6: An invalid region is provided.
      {
          'project_id': 'gcpdiag-bigquery1-aaaa',
          'bigquery_job_id': 'any_id',
          'bigquery_job_region': 'invalid-region',
          'bigquery_skip_permission_check': False,
      },
  ]
