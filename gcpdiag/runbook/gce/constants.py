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
    r'You are in (rescue|emergency) mode',
    r'Started \x1b?\[?.*Emergency Shell',
    r'Reached target \x1b?\[?.*Emergency Mode',
    # GRUB emergency shell.
    'Minimal BASH-like line editing is supported',
    # Grub/EFI corruption check
    r'grub2 error: symbol \'grub_calloc\' not found',
    r'error: symbol \'grub_verify_string\' not found',
    # Typical Kernel logs
    'Kernel panic',
    'Give root password for maintenance',
    r'\(or press Control-D to continue\):',
    'Boot failed: not a bootable disk',
    'Dependency failed for /'
]

SERIAL_LOG_START_POINT = [
    r'Command line: BOOT_IMAGE=\([^()]+\)/boot/vmlinuz-\S+',
    r'Command line: BOOT_IMAGE=/boot/vmlinuz-\S+',  # SUSE
]

FS_CORRUPTION_MSG = [
    'Corruption of in-memory data detected. Shutting down filesystem',
    'Corruption of in-memory data detected', 'warning: mounting fs with errors',
    'Failed to mount /',
    r'A stop job is running for Security \.\.\..* Service ',
    'I/O Error Detected. Shutting down filesystem', 'metadata I/O error in'
]

OOM_PATTERNS = [
    r'Out of memory: Kill(ed)? process',
    r'Kill(ed)? process',
    'Memory cgroup out of memory',
    'invoked oom-killer',
]

NETWORK_ERRORS = [
    'dial tcp 169.254.169.254:80: connect: network is unreachable',
    'dial tcp 169.254.169.254:80: i/o timeout',
    'dial tcp metadata.goog:80: connect: network is unreachable',
    'dial tcp metadata.google.internal:80: connect: network is unreachable',
    'error connecting to metadata server'
]

TIME_SYNC_ERROR = [
    # NTP related error message:
    'time may be out of sync',
    'System clock is unsynchronized',
    'Time drift detected',
    'no servers can be used, system clock unsynchronized',
    'time reset',  # sudden jump in time
    # Chrony-Related error message:
    'System clock unsynchronized',
    'Time offset too large',
    r'Can\'t synchronise: no selectable sources',
    # General Errors:
    'Clock skew detected',  # make, ssh
    'Clock skew too great',  # Kerberos
    'Could not receive latest log timestamp from server',  # PostgreSQL replication
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

DISK_EXHAUSTION_ERRORS = [
    'No space left on device',
    'No usable temporary directory found',
    r'A stop job is running for Security \.\.\..* Service ',
    # windows
    'disk is at or near capacity'
]

SLOW_DISK_READS = [
    # Linux slow read:
    r'\d+:\d+:\d+:\d+: timing out command, waited \d+s',
    r'end_request: I/O error, dev [a-z0-9-]+, sector \d+',
    r'Buffer I/O error on device [a-z0-9-]+, logical block \d+',
    r'blocked for more than \d+ seconds',
    # Linux SCSI commands abort/reset (when operation to PD times out)
    r'\d+:\d+:\d+:\d+:\s+\[([a-z0-9-]+)\]\s+(abort|device reset)$',
    r'\d+:\d+:\d+:\d+:\s+(device reset)$',
    # Linux Local SSD physical failure on console:
    r'kernel: blk_update_request: I/O error, dev [a-z0-9-]+, sector \d+',
    # Windows
    r'The IO operation at logical block address 0x[0-9a-fA-F.]+ for Disk \d+ '
]

GOOD_SSHD_PATTERNS = [
    'Started OpenBSD Secure Shell server', 'Started OpenSSH server daemon',
    'Started OpenSSH Daemon',
    'Started ssh.service - OpenBSD Secure Shell server'
]

BAD_SSHD_PATTERNS = [
    'Failed to start OpenBSD Secure Shell server',
    'Failed to start OpenSSH server', 'Failed to start OpenSSH Daemon'
]

# SSHD Guard blocking logs
SSHGUARD_PATTERNS = [r'sshguard\[\d+\]: Blocking (\d+\.\d+\.\d+\.\d+)']

GCE_CLUSTER_MANAGER_EMAIL = 'cloud-cluster-manager@prod.google.com'

GUEST_AGENT_STATUS_MSG = [
    'Started Google Compute Engine Guest Agent',
    r'google_guest_agent\[\d+\]: GCE Agent Started'
]

GUEST_AGENT_FAILED_MSG = [
    'Failed to start Google Compute Engine Guest Agent',
    r'google_guest_agent\[(\d+)\]: CRITICAL (.*\.go):(\d+) error registering service'
]

SSHD_AUTH_FAILURE = [
    'Authentication refused: bad ownership or modes for directory',
    r'Error updating SSH keys for (\w+): mkdir (.*): no such file or directory'
]
