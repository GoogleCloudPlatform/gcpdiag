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
"""Contains GKE specific flags"""
# pylint: disable=wildcard-import, unused-wildcard-import
from gcpdiag.runbook.gcp.flags import *
# pylint: disable=wildcard-import, unused-wildcard-import
from gcpdiag.runbook.iam.flags import *

LOCATION = 'location'
NODE = 'node'
NODEPOOL = 'nodepool'
GKE_CLUSTER_NAME = 'gke_cluster_name'

OPS_AGENT_EXPORTING_METRICS = False
PROTOCOL_TYPE = 'protocol_type'
INTERACTIVE_MODE = 'auto'
# cluster zone or region
LOCATION = 'location'
POD_IP = 'pod_ip'
GKE_NODE_IP = 'node_ip'
SRC_IP = 'src_ip'
DEST_IP = 'dest_ip'
