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
"""Flags for BigQuery runbooks."""
# pylint: disable=unused-wildcard-import, wildcard-import
from gcpdiag.runbook.gcp.flags import *
from gcpdiag.runbook.iam.flags import *

BQ_JOB_ID = 'bigquery_job_id'
BQ_JOB_REGION = 'bigquery_job_region'
BQ_SKIP_PERMISSION_CHECK = 'bigquery_skip_permission_check'
BQ_PERMISSION_RESULTS = 'bigquery_permission_results'
BQ_JOB_ORGANIZATION_ID = 'bigquery_job_organization_id'
BQ_RESERVATION_ADMIN_PROJECT_ID = 'bigquery_reservations_admin_project_id'
PROJECT_ID = 'project_id'
