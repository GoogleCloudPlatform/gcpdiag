# Copyright 2021 Google LLC
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
"""Parameters applicable to GCE runbooks."""
# pylint: disable=wildcard-import, unused-wildcard-import
from gcpdiag.runbook.gcp.flags import *
from gcpdiag.runbook.iam.flags import *

LOCAL_USER = 'local_user'
TUNNEL_THROUGH_IAP = 'tunnel_through_iap'
CHECK_OS_LOGIN = 'check_os_login'
POSIX_USER = 'posix_user'
ACCESS_METHOD = 'access_method'
INSTANCE_CREATED = 'instance_created'
CHECK_ZONE_SEPARATION_POLICY = 'check_zone_separation_policy'
