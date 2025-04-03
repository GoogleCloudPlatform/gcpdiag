# Copyright 2025 Google LLC
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
"""Guest OS boot-up runbook."""

import mimetypes

import googleapiclient.errors

from gcpdiag import runbook
from gcpdiag.queries import crm, gce
from gcpdiag.runbook import op
from gcpdiag.runbook.gce import constants as gce_const
from gcpdiag.runbook.gce import flags
from gcpdiag.runbook.gce import generalized_steps as gce_gs


class GuestosBootup(runbook.DiagnosticTree):
  """ Google Compute Engine VM Guest OS boot-up runbook.

    This runbook is designed to investigate the various boot-up stages of a Linux or Windows Guest
    OS running on Google Compute Engine. It is intended to help you identify and troubleshoot issues
    that may arise during the boot process. The runbook provides a structured approach to resolve
    issues.

    Key Investigation Areas:

    Boot Issues:
        - Check for Boot issues happening due to Kernel panics
        - Check for GRUB related issues.
        - Check if system failed to find boot disk.
        - Check if Filesystem corruption is causing issues with system boot.
        - Check if "/" Filesystem consumption is causing issues with system boot.

    Cloud-init checks:
        - Check if cloud-init has initialised or started.
        - Check if NIC has received the IP.

    Network related issues:
        - Check if metadata server became unreachable since last boot.
        - Check if there are any time sync related errors.

    Google Guest Agent checks:
        - Check if there are logs related to successful startup of Google Guest Agent.
  """
  parameters = {
      flags.PROJECT_ID: {
          'type': str,
          'help': 'The Project ID associated with the VM',
          'required': True
      },
      flags.INSTANCE_NAME: {
          'type': str,
          'help': 'The name of the VM',
          'required': True
      },
      flags.INSTANCE_ID: {
          'type': str,
          'help': 'The instance-id of the VM'
      },
      flags.ZONE: {
          'type': str,
          'help': 'The Google Cloud zone where the VM is located.',
          'required': True
      },
      flags.SERIAL_CONSOLE_FILE: {
          'type': str,
          'ignorecase': True,
          'help': 'Absolute path of files contailing the Serial console logs,'
                  ' in case if gcpdiag is not able to reach the VM Serial logs.'
                  ' i.e -p serial_console_file="filepath1,filepath2" ',
      }
  }

  def build_tree(self):
    """Construct the diagnostic tree with appropriate steps."""
    start = GuestosBootupStart()
    self.add_start(start)
    # consider leverage LLM to perform anomaly detection
    # or other advanced analysis on serial logs within the VM
    # Check for Boot related issues
    kernel_panic = gce_gs.VmSerialLogsCheck()
    kernel_panic.project_id = op.get(flags.PROJECT_ID)
    kernel_panic.zone = op.get(flags.ZONE)
    kernel_panic.instance_name = op.get(flags.INSTANCE_NAME)
    kernel_panic.serial_console_file = op.get(flags.SERIAL_CONSOLE_FILE)
    kernel_panic.template = 'vm_serial_log::kernel_panic'
    kernel_panic.negative_pattern = gce_const.KERNEL_PANIC_LOGS
    self.add_step(parent=start, child=kernel_panic)

    # Checking for Filesystem corruption related errors
    fs_corruption = gce_gs.VmSerialLogsCheck()
    fs_corruption.project_id = op.get(flags.PROJECT_ID)
    fs_corruption.zone = op.get(flags.ZONE)
    fs_corruption.instance_name = op.get(flags.INSTANCE_NAME)
    fs_corruption.serial_console_file = op.get(flags.SERIAL_CONSOLE_FILE)
    fs_corruption.template = 'vm_serial_log::linux_fs_corruption'
    fs_corruption.negative_pattern = gce_const.FS_CORRUPTION_MSG
    self.add_step(parent=start, child=fs_corruption)

    #Checking for Cloud-init related issues
    cloudinit_issues = CloudInitChecks()
    self.add_step(parent=start, child=cloudinit_issues)

    # Checking for network related errors
    network_issue = gce_gs.VmSerialLogsCheck()
    network_issue.project_id = op.get(flags.PROJECT_ID)
    network_issue.zone = op.get(flags.ZONE)
    network_issue.instance_name = op.get(flags.INSTANCE_NAME)
    network_issue.serial_console_file = op.get(flags.SERIAL_CONSOLE_FILE)
    network_issue.template = 'vm_serial_log::network_errors'
    network_issue.negative_pattern = gce_const.NETWORK_ERRORS
    self.add_step(parent=start, child=network_issue)

    # Check for Guest Agent status
    guest_agent_check = gce_gs.VmSerialLogsCheck()
    guest_agent_check.project_id = op.get(flags.PROJECT_ID)
    guest_agent_check.zone = op.get(flags.ZONE)
    guest_agent_check.instance_name = op.get(flags.INSTANCE_NAME)
    guest_agent_check.serial_console_file = op.get(flags.SERIAL_CONSOLE_FILE)
    guest_agent_check.template = 'vm_serial_log::guest_agent'
    guest_agent_check.positive_pattern = gce_const.GUEST_AGENT_STATUS_MSG
    guest_agent_check.negative_pattern = gce_const.GUEST_AGENT_FAILED_MSG
    self.add_step(parent=start, child=guest_agent_check)
    self.add_end(runbook.EndStep())


class GuestosBootupStart(runbook.StartStep):
  """Fetches VM details and validates the instance state.

  This step retrieves the VM instance details based on the provided project ID,
  zone, and instance name. It checks if the VM is running and updates the
  instance ID or name if missing. Additionally, it performs sanity checks on
  the provided serial console log files to ensure they are valid plain text files.
  """

  template = 'vm_attributes::running'

  def execute(self):
    """Fetching VM details"""

    project = crm.get_project(op.get(flags.PROJECT_ID))
    try:
      vm = gce.get_instance(project_id=op.get(flags.PROJECT_ID),
                            zone=op.get(flags.ZONE),
                            instance_name=op.get(flags.INSTANCE_NAME))
    except googleapiclient.errors.HttpError:
      op.add_skipped(
          project,
          reason=('Instance {} does not exist in zone {} or project {}').format(
              op.get(flags.INSTANCE_NAME), op.get(flags.ZONE),
              op.get(flags.PROJECT_ID)))
    else:
      if vm and vm.is_running:
        # Check for instance id and instance name
        if not op.get(flags.INSTANCE_ID):
          op.put(flags.INSTANCE_ID, vm.id)
        elif not op.get(flags.INSTANCE_NAME):
          op.put(flags.INSTANCE_NAME, vm.name)
      else:
        op.add_failed(vm,
                      reason=op.prep_msg(op.FAILURE_REASON,
                                         full_resource_path=vm.full_path,
                                         status=vm.status),
                      remediation=op.prep_msg(op.FAILURE_REMEDIATION,
                                              full_resource_path=vm.full_path,
                                              status=vm.status))

    # file sanity checks
    if op.get(flags.SERIAL_CONSOLE_FILE):
      for file in op.get(flags.SERIAL_CONSOLE_FILE).split(','):
        try:
          with open(file, 'rb') as f:
            results = mimetypes.guess_type(file)[0]
            if results and not results.startswith('text/'):
              # Peek at content for further clues
              content_start = f.read(1024)  # Read a small chunk
              # Check for gzip and xz magic number (first two bytes)
              if content_start.startswith(
                  b'\x1f\x8b') or content_start.startswith(b'\xfd'):
                op.add_skipped(
                    vm,
                    reason=('File {} appears to be compressed, not plain text.'
                           ).format(file))
              else:
                # If not gzip or tar, try simple text encoding detection (UTF-8, etc.)
                try:
                  content_start.decode()
                except UnicodeDecodeError:
                  op.add_skipped(
                      vm,
                      reason=('File {} does not appear to be plain text.'
                             ).format(file))

        except FileNotFoundError:
          op.add_skipped(
              vm,
              reason=('The file {} does not exists. Please verify if '
                      'you have provided the correct absolute file path'
                     ).format(file))


class CloudInitChecks(runbook.CompositeStep):
  """Cloud init related checks"""

  def execute(self):
    """Cloud init related checks"""
    ubuntu_licenses = gce.get_gce_public_licences('ubuntu-os-cloud')
    ubuntu_pro_licenses = gce.get_gce_public_licences('ubuntu-os-pro-cloud')
    licenses = ubuntu_licenses + ubuntu_pro_licenses
    vm = gce.get_instance(project_id=op.get(flags.PROJECT_ID),
                          zone=op.get(flags.ZONE),
                          instance_name=op.get(flags.INSTANCE_NAME))
    if vm.check_license(licenses):
      # Checking for Cloud init startup log
      cloud_init_startup_check = gce_gs.VmSerialLogsCheck()
      cloud_init_startup_check.project_id = op.get(flags.PROJECT_ID)
      cloud_init_startup_check.zone = op.get(flags.ZONE)
      cloud_init_startup_check.instance_name = op.get(flags.INSTANCE_NAME)
      cloud_init_startup_check.serial_console_file = op.get(
          flags.SERIAL_CONSOLE_FILE)
      cloud_init_startup_check.template = 'vm_serial_log::cloud_init_startup_check'
      cloud_init_startup_check.positive_pattern = gce_const.CLOUD_INIT_STARTUP_PATTERN
      self.add_child(cloud_init_startup_check)

      # Checking if NIC has received IP
      cloud_init_check = gce_gs.VmSerialLogsCheck()
      cloud_init_check.template = 'vm_serial_log::cloud_init'
      cloud_init_check.project_id = op.get(flags.PROJECT_ID)
      cloud_init_check.zone = op.get(flags.ZONE)
      cloud_init_check.instance_name = op.get(flags.INSTANCE_NAME)
      cloud_init_check.serial_console_file = op.get(flags.SERIAL_CONSOLE_FILE)
      cloud_init_check.negative_pattern = gce_const.CLOUD_INIT_NEGATIVE_PATTERN
      cloud_init_check.positive_pattern = gce_const.CLOUD_INIT_POSITIVE_PATTERN
      self.add_child(cloud_init_check)
    else:
      op.add_skipped(
          vm, reason='This VM is not Ubuntu or it does not uses cloud-init')
