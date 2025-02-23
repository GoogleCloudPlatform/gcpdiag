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
"""Parameters applicable to Dataproc runbooks."""
# pylint: disable=wildcard-import, unused-wildcard-import
from gcpdiag.runbook.gcp.flags import *
from gcpdiag.runbook.iam.flags import *

CLUSTER_UUID = 'cluster_uuid'
CLUSTER_NAME = 'cluster_name'
NETWORK = 'network'
SUBNETWORK = 'subnetwork'
REGION = 'region'
STATUS = 'status'
STACKDRIVER = 'stackdriver'
CROSS_PROJECT_ID = 'cross_project'
INTERNAL_IP_ONLY = 'internal_ip_only'
CONSTRAINT = 'constraint'
HOST_VPC_PROJECT_ID = 'host_vpc_project'
IMAGE_VERSION = 'image_version'
JOB_ID = 'job_id'
JOB_EXIST = 'job_exist'
JOB_OLDER_THAN_30_DAYS = 'job_older_than_30_days'
