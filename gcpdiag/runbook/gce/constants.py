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
OS_LOGIN_ROLES = [
    OSLOGIN_ROLE, OSLOGIN_ADMIN_ROLE, 'roles/iam.serviceAccountUser',
    OSLOGIN_EXTERNAL_USER_ROLE
]
ENABLE_OSLOGIN = 'enable-oslogin'
ENABLE_OSLOGIN_2FA = 'enable-oslogin-2fa'
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
    'dial tcp metadata.google.internal:80: connect: network is unreachable'
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

# Cloud init checks
CLOUD_INIT_POSITIVE_PATTERN = [r'ci-info: [|].*[|]\sTrue\s[|]']
CLOUD_INIT_NEGATIVE_PATTERN = [r'ci-info: [|].*[|]\sFalse\s[|]']
CLOUD_INIT_STARTUP_PATTERN = [
    r"cloud-init\[(\d+)\]: Cloud-init v\. (.*?) running '(.*)'"
]

# OS Config
ENABLE_OSCONFIG = 'enable-osconfig'

# GCE Operation types
IG_INSTANCE_REPAIR_METHOD = 'compute.instances.repair.recreateInstance'
INSTANCE_PREMPTION_METHOD = 'compute.instances.preempted'
HOST_ERROR_METHOD = 'compute.instances.hostError'
STOP_METHOD = 'compute.instances.stop'
TERMINATE_ON_HOST_MAINTENANCE_METHOD = 'compute.instances.terminateOnHostMaintenance'
GUEST_TERMINATE_METHOD = 'compute.instances.guestTerminate'

GCE_ACTIVITY_LOG_FILTER = ('logName:"cloudaudit.googleapis.com%2Factivity" '
                           'protoPayload.serviceName:"compute.googleapis.com"')

# MIG
AUTOSCALING_MODE_ON = 'ON'
AUTOSCALING_MODE_OFF = 'OFF'
MIG_LIMIT_EXCEEDED_LOGS = ["Exceeded limit 'MAX_INSTANCES_IN_INSTANCE_GROUP'"]
MIG_NOT_FOUND_LOGS = ['instanceGroupManagers.*was not found']
MIG_IN_USE_LOGS = ['is already being used by']
MIG_MANAGER_RESOURCE_TYPE_FILTER = 'resource.type="gce_instance_group_manager"'
MIG_RESOURCE_TYPE_FILTER = 'resource.type="gce_instance_group_manager"'

# OS Checks
RHEL_PATTERN = 'rhel'
ROCKY_PATTERN = 'rocky'
SLES_PATTERN = 'sles'
WINDOWS_FEATURE = 'WINDOWS'
BYOS_PATTERN = 'byos'
PROP_BOOT_DISK_LICENSES = 'boot_disk_licenses'
PROP_GUEST_OS_FEATURES = 'guest_os_features'
PROP_NETWORK_INTERFACE_COUNT = 'network_interface_count'
PROP_IS_PREEMPTIBLE_VM = 'is_preemptible_vm'
PROP_CREATED_BY_MIG = 'created_by_mig'

# Reservation errors
RESERVATION_RESIZE_COUNT_TOO_LOW = [
    'The resize instance count cannot be lower than the in use count for a specific reservation.'
]
RESERVATION_POLICY_IN_USE = [
    r'The resource_policy resource \'projects/.+/regions/.+/resourcePolicies/.+\' '
    r'is already being used by \'projects/.+/zones/.+/reservations/.+\'.'
]
RESERVATION_MACHINE_TYPE_DISALLOWED = [
    r'The machine type .+ provided in instance properties is disallowed for '
    'reservations with ANY reservation affinity'
]
RESERVATION_SHARED_NO_ORG = [
    'Cannot create Shared Reservations in a project that does not belong to an organization.'
]
RESERVATION_INVALID_DISK_SIZE = [
    r'Disk .+ provided in the instance template has invalid size: 0 GB.'
]
RESERVATION_OUTSIDE_ZONE_REGION = [
    'Reservation cannot be created outside the zone/region of source resource.'
]
RESERVATION_INVALID_SOURCE_RESOURCE = [
    'Source resource reference provided invalid.'
]
RESERVATION_ALREADY_EXISTS = [
    r'The resource \'projects/.+/zones/.+/.+/.+\' already exists'
]
RESERVATION_NOT_FOUND = ['notFound', 'does not exist in zone']
RESERVATION_CANNOT_OVERRIDE_PROPERTIES = [
    'Reservation cannot override properties populated by source resource.'
]
RESERVATION_CROSS_PROJECT_REFERENCE_NOT_ALLOWED = [
    'Cross project referencing is not allowed for this resource.'
]
RESERVATION_SHARED_LIMIT_EXCEEDED = [
    'Cannot support more than 100 shared reservations of the same shape under an organization.'
]
RESERVATION_INVALID_SPECIFIC_RESERVATION_COUNT = [
    'Invalid value for field \'resource.specificReservation.count\''
]
RESERVATION_SHARED_OWNER_PROJECTS_CONSTRAINT = [
    'Constraint constraints/compute.sharedReservationsOwnerProjects violated for '
    'project'
]
RESERVATION_PROJECT_NOT_FOUND_OR_ORG = [
    r'Project .+ doesn\'t exist or doesn\'t belong to the same organization of '
    'the current project.'
]

# Reservation filters
RESERVATION_CREATE_SUCCESS_FILTER = (
    'protoPayload.methodName=\'compute.reservations.create\' AND '
    'protoPayload.status.code=200')
RESERVATION_UPDATE_SUCCESS_FILTER = (
    'protoPayload.methodName=\'compute.reservations.update\' AND '
    'protoPayload.status.code=200')
