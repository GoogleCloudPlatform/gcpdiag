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
"""Constants applicable relevant to only dataproc implementation."""
# pylint: disable=unused-wildcard-import, wildcard-import
from gcpdiag.runbook.iam.constants import *

PORT_EXHAUSTION_LOG = (
    "Address already in use: Service 'sparkDriver' failed after 1000 retries")

SW_PREEMPTION_LOG = (
    '(requesting driver to remove executor | lost executor | Container'
    ' released on a lost node)')

WORKER_DISK_USAGE_LOG = (
    'Most of the disks failed. 1/1 local-dirs usable space is below'
    ' utilization percentage/no more usable space')

GC_PAUSE_LOG = 'Detected pause in JVM or host machine (eg GC)'

KILL_ORPHANED_APP_LOG = 'Killing orphaned yarn application'

PYTHON_IMPORT_LOG = 'ImportError: cannot import name'

SHUFFLE_KILL_LOG = 'Executor is not registered'

TOO_MANY_JOBS_LOG = 'Too many running jobs'

NOT_ENOUGH_MEMORY_LOG = 'Not enough free memory'

SYSTEM_MEMORY_LOG = 'High system memory usage'

RATE_LIMIT_LOG = 'Rate limit'

NOT_INITIALIZED_LOG = 'Master agent not initialized'

NOT_ENOUGH_DISK_LOG = 'Disk space too low on Master'

YARN_RUNTIME_LOG = ('YarnRuntimeException: Could not load history file .*'
                    ' /mapreduce-job-history/intermediate-done/root')

ERROR_403_LOG = ('com.google.cloud.hadoop.repackaged.gcs.com.google.api.client.'
                 'googleapis.json.GoogleJsonResponseException: 403 Forbidden')

ERROR_429_GCE_LOG = (
    'com.google.cloud.hadoop.repackaged.gcs.com.google.api.client.http.'
    'HttpResponseException: 429 Too Many Requests')

ERROR_429_DRIVER_LOG = (
    'com.google.cloud.hadoop.services.repackaged.com.google.api.client.'
    'googleapis.json.GoogleJsonResponseException: 429 Too Many Requests')

ERROR_412_LOG = (
    'com.google.cloud.hadoop.repackaged.gcs.com.google.api.client.'
    'googleapis.json.GoogleJsonResponseException: 412 Precondition Failed')

BQ_RESOURCE_LOG = ('com.google.cloud.spark.bigquery.repackaged.io.grpc.'
                   'StatusRuntimeException: RESOURCE_EXHAUSTED')
