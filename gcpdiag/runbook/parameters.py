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
"""Common parameter flags applicable to any runbook"""
PROJECT_ID = 'project_id'
NAME_FLAG = 'name'
ZONE_FLAG = 'zone'
# unique flags belong to this runbook
TTI_FLAG = 'tunnel_through_iap'
PRINCIPAL_FLAG = 'principal'
SRC_IP_FLAG = 'src_ip'
DEST_IP_FLAG = 'dest_ip'
OS_LOGIN_FLAG = 'os_login'
LOCAL_USER_FLAG = 'local_user'
PORT_FLAG = 'port'
PROTOCOL_TYPE = 'protocol_type'
START_TIME_UTC = 'start_time_utc'
END_TIME_UTC = 'end_time_utc'

# Runbook Flags
# Move this into superclass when using classes
AUTO = 'auto'
