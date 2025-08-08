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
"""Flags for Dataflow runbooks."""
# pylint: disable=unused-wildcard-import, wildcard-import
from gcpdiag.runbook.gcp.flags import *
from gcpdiag.runbook.iam.flags import *

JOB_ID = 'job_id'
JOB_REGION = 'job_region'
WORKER_SERVICE_ACCOUNT = 'worker_service_account'
PRINCIPAL = 'principal'
CROSS_PROJECT_ID = 'cross_project_id'
DATAFLOW_JOB_ID = 'dataflow_job_id'
