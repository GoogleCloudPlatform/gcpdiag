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
"""Constants applicable relevant to only gce implementation"""
import ipaddress

# pylint: disable=unused-wildcard-import, wildcard-import
from gcpdiag.runbook.gcp.constants import *
from gcpdiag.runbook.iam.constants import *

# Os login Permissions
OSLOGIN_ROLE = 'roles/compute.osLogin'
OSLOGIN_ADMIN_ROLE = 'roles/compute.osAdminLogin'
# Users from a different organization than the VM they're connecting to
OSLOGIN_EXTERNAL_USER_ROLE = 'roles/compute.osLoginExternalUser'
# INSTANCE ADMIN
INSTANCE_ADMIN_ROLE = 'roles/compute.instanceAdmin.v1'

# Networking
IAP_FW_VIP = ipaddress.ip_network('35.235.240.0/20')
UNSPECIFIED_ADDRESS = ipaddress.ip_network('0.0.0.0/0')
DEFAULT_SSHD_PORT = 22
NEXT_HOP = 'default-internet-gateway'

# Guest OS logs
KERNEL_PANIC_LOGS = [
    'Security Violation',
    # GRUB not being able to find image.
    'Failed to load image',
    # OS emergency mode (emergency.target in systemd).
    'You are now being dropped into an emergency shell',
    'You are in (rescue|emergency) mode',
    r'Started \x1b?\[?.*Emergency Shell',
    r'Reached target \x1b?\[?.*Emergency Mode',
    # GRUB emergency shell.
    'Minimal BASH-like line editing is supported',
    # Typical Kernel logs
    'Kernel panic',
]

# Typical logs of a fully booted windows VM
GOOD_WINDOWS_BOOT_LOGS_READY = [
    'BdsDxe: starting',
    'UEFI: Attempting to start image',
    'Description: Windows Boot Manager',
    'GCEGuestAgent: GCE Agent Started',
    'OSConfigAgent Info: OSConfig Agent',
    'GCEMetadataScripts: Starting startup scripts',
]

GOOD_SSHD_PATTERNS = ['Starting OpenBSD Secure Shell server']
BAD_SSHD_PATTERNS = ['Failed to start OpenBSD Secure Shell server']

# SSHD Guard blocking logs
SSHGUARD_PATTERNS = [r'sshguard\[\d+\]: Blocking (\d+\.\d+\.\d+\.\d+)']
