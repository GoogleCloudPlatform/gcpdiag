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
"""TODO: String doc"""

from gcpdiag.runbook.gcp.constants import *
from gcpdiag.runbook.iam.constants import *

DATAFLOW_SERVICE_AGENT_ROLE = 'roles/dataflow.serviceAgent'
DATAFLOW_WORKER_ROLE = 'roles/dataflow.worker'
DATAFLOW_DEVELOPER_ROLE = 'roles/dataflow.developer'
DATAFLOW_IAM_SERVICE_ACCOUNT_USER = 'roles/iam.serviceAccountUser'

# product errors
GENERIC_ERR = 'Error logs found in job logs for the project'
BATCH_JOB_FAILED_ERR = 'The job failed because a work item has failed 4 times.'
BATCH_WORKER_STARTUP_FAILURE1 = 'failed to StartContainer'
BATCH_WORKER_STARTUP_FAILURE2 = (
  'The Dataflow job appears to be stuck because no worker activity has been seen'
)
BATCH_WORKER_STARTUP_FAILURE3 = 'Error syncing pod.*StartContainer.*'
BATCH_WORKER_STARTUP_CONFIRMATION = 'Workers have started successfully'
BATCH_OUT_OF_MEMORY_FAILURE1 = 'out of memory'
BATCH_OUT_OF_MEMORY_FAILURE2 = 'OutOfMemory'
BATCH_OUT_OF_MEMORY_FAILURE3 = 'Shutting down JVM'
BAD_MACHINE_TYPE_FAILURE1 = 'Unable to get machine type information for machine type'
BAD_MACHINE_TYPE_FAILURE2 = 'features are not compatible for creating instance'
STOCKOUT_ERR1 = 'RESOURCE_POOL_EXHAUSTED'
STOCKOUT_ERR2 = 'ZONE_RESOURCE_POOL_EXHAUSTED'
TOO_HIGH_VOLUME_LOGGING = 'Throttling logger worker. It used up its 30s quota for logs'

GENERIC_WARNING = (
  'Warning/error logs found in job logs for the project. Some errors may be transient.',
  'Please check Dataflow common error docs for the specific error remediation',
)
