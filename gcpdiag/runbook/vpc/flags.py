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
"""Flags used in the VPC runbook"""
# pylint: disable=unused-wildcard-import, wildcard-import

from gcpdiag.runbook.flags import *
from gcpdiag.runbook.gcp.flags import *

PROJECT_ID = 'project_id'
PROJECT_NUMBER = 'project_number'
FOLDER_ID = 'folder_id'
ORG_ID = 'org_id'
NAME = 'name'
ID = 'id'
REGION = 'region'
ZONE = 'zone'

# unique flags belong to this runbook
SRC_IP = 'src_ip'
DEST_IP = 'dest_ip'
SRC_NIC = 'src_nic'
DEST_PORT = 'dest_port'
PORT = 'port'
PROTOCOL_TYPE = 'protocol_type'
