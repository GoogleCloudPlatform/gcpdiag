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

# pylint: disable=unused-wildcard-import
# pylint: disable=wildcard-import
from gcpdiag.runbook.constants import *
from gcpdiag.runbook.iam.constants import *

BOOL_VALUES = {
    'y': True,
    'yes': True,
    'true': True,
    '1': True,
    'n': False,
    'no': False,
    'false': False,
    '0': False,
    None: False
}
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

KERNEL_PANIC_FAILURE_REMEDIATION = (
    'To resolve the kernel panic, follow these '
    'steps:\n1. Review general guidance on resolving kernel panic errors:\n'
    'https://cloud.google.com/compute/docs/troubleshooting/kernel-panic'
    '#resolve_the_kernel_panic_error\n'
    '2. Check for potential errors in the `/etc/fstab` file:\n'
    'https://cloud.google.com/compute/docs/troubleshooting/fstab-errors\n'
    '3. If the GRUB_TIMEOUT is greater than 0, use the serial console to establish an'
    'interactive session:\n'
    'https://cloud.google.com/compute/docs/troubleshooting/'
    'troubleshooting-using-serial-console\n'
    '4. As an alternative, rescue an inaccessible VM by following the instructions here:\n'
    'https://cloud.google.com/compute/docs/troubleshooting/rescue-vm\n\n'
    'NOTE: Guest Related issues is Out of Support Scope\n'
    'See GCP support policy on Guest OS\n'
    'https://cloud.google.com/compute/docs/images/'
    'support-maintenance-policy#support-scope\n'
    'https://cloud.google.com/compute/docs/images/'
    'support-maintenance-policy#out-of-scope_for_support')

KERNEL_PANIC_UNCERTAIN_REMEDIATION = (
    'VM is up and running so check serial '
    'logs for possible issues.\n'
    'https://cloud.google.com/compute/docs/troubleshooting/viewing-serial-port-output\n'
    'if there is a Guest Kernel issue. Resolve the issue using our documentation\n'
    'https://cloud.google.com/compute/docs/troubleshooting/'
    'kernel-panic#resolve_the_kernel_panic_error\n\n'
    'NOTE: Faults within the Guest OS is Out of Support Scope\n'
    'See GCP support policy on Guest OS\n'
    'https://cloud.google.com/compute/docs/images/'
    'support-maintenance-policy#support-scope\n'
    'https://cloud.google.com/compute/docs/images/'
    'support-maintenance-policy#out-of-scope_for_support')

KERNEL_PANIC_UNCERTAIN_REASON = 'No serial logs data to examine'
KERNEL_PANIC_SUCCESS_REASON = (
    'Linux OS is not experiencing kernel panic issue,'
    ' GRUB issues\nor guest kernel dropping into emergency/maintenance mode')

KERNEL_PANIC_FAILURE_REASON = 'The {} is experiencing a kernel panic, preventing correct startup.'

GOOD_SSHD_PATTERNS = ['Starting OpenBSD Secure Shell server']
BAD_SSHD_PATTERNS = ['Failed to start OpenBSD Secure Shell server']

SSHD_FAILURE_REASON = 'SSHD has failed in the VM'
SSHD_FAILURE_REMEDIATION = (
    'Resources on how to fix SSHD issues:\n'
    'https://cloud.google.com/compute/docs/troubleshooting/'
    'troubleshooting-ssh-errors#linux_errors\n'
    'https://cloud.google.com/knowledge/kb/ssh-in-cloud-serial'
    '-console-fails-with-warning-message-000004554\n'
    'NOTE: Faults within the Guest OS is Out of Support Scope\n'
    'See GCP support policy on Guest OS\n'
    'https://cloud.google.com/compute/docs/images/'
    'support-maintenance-policy#support-scope\n'
    'https://cloud.google.com/compute/docs/images/'
    'support-maintenance-policy#out-of-scope_for_support')
SSHD_SUCCESS_REASON = 'SSHD has failed in the VM'
SSHD_UNCERTAIN_REASON = 'We cannot tell if SSHD is faulty or not. Manually investigate'
SSHD_UNCERTAIN_REMEDIATION = (
    'Resources on how to fix SSHD issues:\n'
    'https://cloud.google.com/compute/docs/troubleshooting/'
    'troubleshooting-ssh-errors#linux_errors\n'
    'https://cloud.google.com/knowledge/kb/ssh-in-cloud-serial'
    '-console-fails-with-warning-message-000004554\n\n'
    'NOTE: Guest related issues is Out of Support Scope\n'
    'See GCP support policy on Guest OS\n'
    'https://cloud.google.com/compute/docs/images/'
    'support-maintenance-policy#support-scope\n'
    'https://cloud.google.com/compute/docs/images/'
    'support-maintenance-policy#out-of-scope_for_support')

# SSHD Guard blocking logs
SSHGUARD_PATTERNS = [r'sshguard\[\d+\]: Blocking (\d+\.\d+\.\d+\.\d+)']

SSHGUARD_FAILURE_REASON = ('SSHGuard is enabled and blocking IPs the VM'
                           'check to make sure your IP is not blocked.')
SSHGUARD_FAILURE_REMEDIATION = (
    'NOTE: SSHGuard related issues are Out of Support Scope\n'
    'See GCP support policy on Guest OS\n'
    'https://cloud.google.com/compute/docs/images/'
    'support-maintenance-policy#support-scope\n'
    'https://cloud.google.com/compute/docs/images/'
    'support-maintenance-policy#out-of-scope_for_support')
SSHGUARD_SUCCESS_REASON = 'SSHguard not blocking IPs on the VM'
SSHGUARD_UNCERTAIN_REASON = 'No Serial Logs data to examine'
SSHGUARD_UNCERTAIN_REMEDIATION = (
    'Manually investigate SSHDGuard via interactive serial console\n'
    'https://cloud.google.com/compute/docs/troubleshooting/'
    'troubleshooting-using-serial-console')

WINDOWS_BOOTUP_FAILURE_REASON = 'Windows OS has not booted up correctly'
WINDOWS_BOOTUP_FAILURE_REMEDIATION = (
    'Follow this documentation to ensure that VM is fully booted\n'
    'https://cloud.google.com/compute/docs/troubleshooting/troubleshooting-windows\n'
    'https://cloud.google.com/compute/docs/troubleshooting/'
    'troubleshooting-rdp#instance_ready')
WINDOWS_BOOTUP_SUCCESS_REASON = 'Windows OS serial logs show guest os is has started correctly'
WINDOWS_BOOTUP_UNCERTAIN_REASON = 'Insufficient evidence that Windows OS started correctly'
WINDOWS_BOOTUP_UNCERTAIN_REMEDIATION = (
    'Follow this documentation to ensure that VM is fully booted\n'
    'https://cloud.google.com/compute/docs/troubleshooting/troubleshooting-windows\n'
    'https://cloud.google.com/compute/docs/troubleshooting/'
    'troubleshooting-rdp#instance_ready')
WINDOWS_SSH_MD_FAILURE_REASON = 'SSH metadata is not enabled for the windows instance'
WINDOWS_SSH_MD_FAILURE_REMEDIATION = (
    'Enable SSH on Windows. Follow this guide:\n'
    'https://cloud.google.com/compute/docs/connect/windows-ssh#enable')
WINDOWS_SSH_MD_SUCCESS_REASON = 'SSH is enabled for windows VM.'

WINDOWS_GCE_SSH_AGENT_UNCERTAIN_REASON = 'Not certain google-compute-engine-ssh agent is installed'
WINDOWS_GCE_SSH_AGENT_UNCERTAIN_REMEDIATION = (
    'RDP or use a startup script to verify agent'
    ' availability\nhttps://cloud.google.com/compute/docs/connect/windows-ssh#startup-script'
)
WINDOWS_GCE_SSH_AGENT_SUCCESS_REASON = 'Confirmed google-compute-engine-ssh is on windows VM'
WINDOWS_GCE_SSH_AGENT_FAILURE_REASON = 'Not certain google-compute-engine-ssh agent is installed'
WINDOWS_GCE_SSH_AGENT_FAILURE_REMEDIATION = (
    'Verify/install agent availability and proper configuration.\n'
    'https://cloud.google.com/compute/docs/connect/windows-ssh#startup-script')
