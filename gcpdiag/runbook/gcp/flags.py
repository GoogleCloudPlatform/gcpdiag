# Copyright 2023 Google LLC
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
"""Common parameter flags applicable to any gcp runbook"""

# pylint:disable=wildcard-import,unused-wildcard-import
from gcpdiag.runbook.flags import *

PROJECT_ID = 'project_id'
PROJECT_NUMBER = 'project_number'
FOLDER_ID = 'folder_id'
ORG_ID = 'org_id'
NAME = 'name'
ID = 'id'
INSTANCE_NAME = 'instance_name'
INSTANCE_ID = 'instance_id'
REGION = 'region'
ZONE = 'zone'
SERIAL_CONSOLE_FILE = 'serial_console_file'
# unique flags belong to this runbook
PROXY = 'proxy'
SRC_IP = 'src_ip'
DEST_IP = 'dest_ip'
CLIENT = 'check_os_login'
POSIX_USER = 'local_user'
PORT = 'port'
PROTOCOL_TYPE = 'protocol_type'
PRINCIPAL_TYPE = 'principal_type'
CLIENT = 'client'
MFA = 'mfa'
