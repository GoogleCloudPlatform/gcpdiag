#
# Copyright 2023 Google LLC
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
"""Module containing SSH diagnostic tree and custom steps."""
import ipaddress

import googleapiclient.errors

from gcpdiag import config, runbook
from gcpdiag.queries import crm, gce, iam, monitoring
from gcpdiag.runbook import op
from gcpdiag.runbook.crm import generalized_steps as crm_gs
from gcpdiag.runbook.gce import constants as gce_const
from gcpdiag.runbook.gce import flags
from gcpdiag.runbook.gce import generalized_steps as gce_gs
from gcpdiag.runbook.gce import util
from gcpdiag.runbook.gcp import generalized_steps as gcp_gs
from gcpdiag.runbook.iam import generalized_steps as iam_gs

CHECK_SSH_IN_BROWSER = 'check_ssh_in_browser'
CHECK_CLOUD_CLI = 'check_cloud_cli'
CHECK_IAP_DESKTOP = 'check_iap_desktop'


class Ssh(runbook.DiagnosticTree):
  """A comprehensive troubleshooting guide for common issues which affects SSH connectivity to VMs.

  This runbook focuses on investigating components required for ssh on either Windows and Linux VMs
  hosted on Google Cloud Platform and pinpoint misconfigurations.

  Areas Examined:

  - VM Instance Status: Evaluates the VM's current state, performance - ensuring that it is running
    and not impaired by high CPU usage, insufficient memory, or disk space issues that might disrupt
    normal SSH operations.

  - User Permissions: Checks for the necessary Google Cloud IAM permissions that are required to
    leverage OS Login features and to use metadata-based SSH keys for authentication.

  - VM Configuration: Analyzes the VM's metadata settings to confirm the inclusion of SSH keys,
    flags and other essential configuration details that facilitate SSH access.

  - GCE Network Connectivity Tests: Reviews applicable firewall rules to verify that there are no
    network barriers preventing SSH access to the VM.

  - Internal Guest OS Checks: Analysis available Guest OS metrics or logs to detect any
    misconfigurations or service disruptions that could be obstructing SSH functionality.

  - SSH in Browser Checks: Checks if the authenticated user has relevant permissions and
    the organization policies permits SSH in Browser.
    """
  # Specify parameters common to all steps in the diagnostic tree class.
  parameters = {
      flags.PROJECT_ID: {
          'type': str,
          'help': 'The ID of the project hosting the GCE VM',
          'required': True
      },
      flags.NAME: {
          'type': str,
          'help': 'The name of the target GCE VM',
          'group': 'instance'
      },
      flags.ID: {
          'type': int,
          'help': 'The instance ID of the target GCE VM',
          'group': 'instance'
      },
      flags.ZONE: {
          'type': str,
          'help': 'The zone of the target GCE VM',
          'required': True
      },
      flags.PRINCIPAL: {
          'type': str,
          'help': ('The user or service account principal initiating '
                   'the SSH connection this user should be authenticated in '
                   'gcloud/cloud console when sshing into to the GCE. '
                   'For service account impersonation, it should be the '
                   'service account\'s email'),
          'required': True
      },
      flags.LOCAL_USER: {
          'type': str,
          'help': 'Poxis User on the VM',
      },
      flags.TUNNEL_THROUGH_IAP: {
          'type': bool,
          'help':
              ('A boolean parameter (true or false) indicating whether ',
               'Identity-Aware Proxy should be used for establishing the SSH '
               'connection.'),
          'default': True,
      },
      flags.CHECK_OS_LOGIN: {
          'type': bool,
          'help': ('A boolean value (true or false) indicating whether OS '
                   'Login should be used for SSH authentication'),
          'default': True,
      },
      flags.SRC_IP: {
          'type':
              ipaddress.IPv4Address,
          'help': (
              'Source IP address. Workstation connecting from workstation,'
              'Ip of the bastion/jumphost if currently on logged on a basition/jumphost '
          )
      },
      flags.PROTOCOL_TYPE: {
          'type': str,
          'help': 'Protocol used to connect to SSH',
          'default': 'tcp',
      },
      flags.PORT: {
          'type': int,
          'help': 'Port used to connect to SSH',
          'default': gce_const.DEFAULT_SSHD_PORT
      },
      CHECK_SSH_IN_BROWSER: {
          'type': bool,
          'help': 'Check that SSH in Browser is feasible',
          'default': False
      }
  }

  def build_tree(self):
    start = SshStart()
    lifecycle_check = gce_gs.VmLifecycleState()
    performance_check = VmPerformanceChecks()
    gce_permission_check = GcpSshPermissions()
    gce_firewall_check = GceFirewallAllowsSsh()
    # Prepare parameters given by the user
    # Inform the user values that will be used.
    self.add_start(step=start)
    # First check VM is running
    self.add_step(parent=start, child=lifecycle_check)
    # Only check performance if VM is up and running.
    self.add_step(parent=lifecycle_check, child=performance_check)
    # Check the state of the guest os after performance checks
    self.add_step(parent=lifecycle_check, child=VmGuestOsType())
    # gce_* checks are not depend on the lifecycle, performnce or guest of the VM
    # assign add as a child of start
    self.add_step(parent=start, child=gce_permission_check)
    self.add_step(parent=start, child=gce_firewall_check)

    # Check for Guest Agent status
    guest_agent_check = gce_gs.VmSerialLogsCheck()
    guest_agent_check.template = 'vm_serial_log::guest_agent'
    guest_agent_check.positive_pattern = gce_const.GUEST_AGENT_STATUS_MSG
    guest_agent_check.negative_pattern = gce_const.GUEST_AGENT_FAILED_MSG
    self.add_step(parent=start, child=guest_agent_check)

    # Check for SSH issues due to bad permissions
    sshd_auth_failure = gce_gs.VmSerialLogsCheck()
    sshd_auth_failure.template = 'vm_serial_log::sshd_auth_failure'
    sshd_auth_failure.negative_pattern = gce_const.SSHD_AUTH_FAILURE
    self.add_step(parent=start, child=sshd_auth_failure)

    # users wants to use SSH in Browser
    if op.get(CHECK_SSH_IN_BROWSER):
      self.add_step(parent=start, child=SshInBrowserCheck())
    self.add_end(step=SshEnd())


class SshStart(runbook.StartStep):
  """Initiates diagnostics for SSH connectivity issues.

  This step prepares the environment for SSH diagnostics by gathering necessary
  information about the target VM. It verifies the existence of the VM, checks
  user-supplied parameters for validity, and sets up initial conditions for further
  diagnostic steps.
  """

  def execute(self):
    """Starting SSH diagnostics"""
    project = crm.get_project(op.get(flags.PROJECT_ID))
    try:
      vm = gce.get_instance(project_id=op.get(flags.PROJECT_ID),
                            zone=op.get(flags.ZONE),
                            instance_name=op.get(flags.NAME))
    except googleapiclient.errors.HttpError:
      op.add_skipped(
          project,
          reason=('Instance {} does not exist in zone {} or project {}').format(
              op.get(flags.NAME), op.get(flags.ZONE), op.get(flags.PROJECT_ID)))
    else:
      if vm:
        # Check for instance id and instance name
        if not op.get(flags.ID):
          op.put(flags.ID, vm.id)
        elif not op.get(flags.NAME):
          op.put(flags.NAME, vm.name)
        # prep authenticated principal
        if op.get(flags.PRINCIPAL):
          email_only = len(op.get(flags.PRINCIPAL).split(':')) == 1
          if email_only:
            # Get the type
            p_policy = iam.get_project_policy(vm.project_id)
            p_type = p_policy.get_member_type(op.get(flags.PRINCIPAL))
            op.put(flags.PRINCIPAL, f'{p_type}:{op.get(flags.PRINCIPAL)}')
            if p_type:
              op.info(
                  f'Checks will use {op.get(flags.PRINCIPAL)} as the authenticated\n'
                  'principal in Cloud Console / gcloud (incl. impersonated service account)'
              )
        #
        if not op.get(flags.SRC_IP) and not op.get(
            flags.TUNNEL_THROUGH_IAP) and vm.is_public_machine():
          op.put(flags.SRC_IP, gce_const.UNSPECIFIED_ADDRESS)

        if op.get(flags.TUNNEL_THROUGH_IAP):
          # set IAP VIP as the source to the VM
          op.put(flags.SRC_IP, gce_const.IAP_FW_VIP)
          op.info('Will check for IAP configuration')
        else:
          op.info('Will not check for IAP for TCP forwarding configuration')

        op.info(
            f'Runbook will use Protocol {op.get(flags.PROTOCOL_TYPE)},'
            f'Port {op.get(flags.PORT)} and ip {op.get(flags.SRC_IP)} as the source IP'
        )

        if op.get(flags.CHECK_OS_LOGIN):
          op.info(
              'Runbook will check if OS login is correctly configured to permit SSH'
          )
        else:
          op.info(
              'Runbook will check if Key-based SSH approached is are correctly configured'
          )

        if op.get(flags.LOCAL_USER):
          op.info(f'Local User: {op.get(flags.LOCAL_USER)} will be used '
                  f'examine metadata-based SSH Key configuration')

        if op.get(CHECK_SSH_IN_BROWSER):
          op.info(
              'Runbook will investigate components required for SSH in browser')
        else:
          op.info(
              'Runbook will not investigate components required for SSH in browser'
          )

    ops_agent_q = monitoring.query(
        op.get(flags.PROJECT_ID), """
              fetch gce_instance
              | metric 'agent.googleapis.com/agent/uptime'
              | filter (metadata.system_labels.name == '{}')
              | align rate(5m)
              | every 5m
              | {}
            """.format(op.get(flags.NAME), gce_gs.within_str))
    if ops_agent_q:
      op.info(
          'Runbook Will use ops agent metrics for VM Performance investigation')
      op.put(flags.OPS_AGENT_EXPORTING_METRICS, True)


class VmGuestOsType(runbook.Gateway):
  """Distinguishes between Windows and Linux operating systems on a VM to guide further diagnostics.

  Based on the OS type, it directs the diagnostic process towards OS-specific checks,
  ensuring relevancy and efficiency in troubleshooting efforts.
  """

  def execute(self):
    """Identifying Guest OS type..."""
    vm = gce.get_instance(project_id=op.get(flags.PROJECT_ID),
                          zone=op.get(flags.ZONE),
                          instance_name=op.get(flags.NAME))
    if not vm.is_windows_machine():
      op.info('Detected Linux VM. Proceeding with Linux-specific diagnostics.')
      self.add_child(LinuxGuestOsChecks())
    else:
      op.info(
          'Detected Windows VM. Proceeding with Windows-specific diagnostics.')
      self.add_child(WindowsGuestOsChecks())


class SshEnd(runbook.EndStep):
  """Concludes the SSH diagnostics process, offering guidance based on the user's feedback.

  If SSH issues persist, it directs the user to helpful resources and
  suggests contacting support with a detailed report
  """

  def execute(self):
    """Finalizing SSH diagnostics..."""
    if not config.get(flags.INTERACTIVE_MODE):
      response = op.prompt(
          kind=op.CONFIRMATION,
          message=f'Are you able to SSH into VM {op.get(flags.NAME)}?',
          choice_msg='Enter an option: ')
      if response == op.NO:
        op.info(message=op.END_MESSAGE)


class SshInBrowserCheck(runbook.CompositeStep):
  """Investigate SSH in Browser components

  SSH can be done via SSH in Browser feature, if desired by user,
  check components required for SSH in browser to work correctly
  """

  def execute(self):
    """SSH in browser required?"""
    ssh_in_browser_orgpolicy_check = crm_gs.OrgPolicyCheck()
    ssh_in_browser_orgpolicy_check.constraint = 'constraints/compute.disableSshInBrowser'
    ssh_in_browser_orgpolicy_check.is_enforced = False
    self.add_child(ssh_in_browser_orgpolicy_check)
    # add check constraints/compute.vmExternalIpAccess when list org policies are allowed.


class GcpSshPermissions(runbook.CompositeStep):
  """Evaluates the user's GCP permissions against the requirements for accessing a VM via SSH.

  This step checks if the user has the necessary project-level roles
  for both traditional SSH access and OS Login methods. It does not consider permissions inherited
  from higher-level resources such as folders, organizations, or groups.
  """

  def execute(self):
    """Verifying overall user permissions for SSH access...

    Note: Only roles granted at the project level are checked. Permissions inherited from
    ancestor resources such as folder(s) or organization and groups are not checked."""
    # Check user has permisssion to access the VM in the first place
    if op.get(CHECK_SSH_IN_BROWSER):
      console_permission = iam_gs.IamPolicyCheck()
      console_permission.template = 'gcpdiag.runbook.gce::permissions::console_view_permission'
      console_permission.permissions = ['compute.projects.get']
      console_permission.require_all = False
      self.add_child(console_permission)
    # Both OS login and gcloud key based require this.
    instance_fetch_perm_check = iam_gs.IamPolicyCheck()
    instance_fetch_perm_check.template = 'gcpdiag.runbook.gce::permissions::instances_get'
    instance_fetch_perm_check.permissions = [
        'compute.instances.get', 'compute.instances.use'
    ]
    instance_fetch_perm_check.require_all = False
    self.add_child(instance_fetch_perm_check)

    # Check OS login or Key based auth preference.
    self.add_child(OsLoginStatusCheck())

    if op.get(flags.TUNNEL_THROUGH_IAP):
      iap_role_check = iam_gs.IamPolicyCheck()
      iap_role_check.template = 'gcpdiag.runbook.gce::permissions::iap_role'
      iap_role_check.roles = [gce_const.IAP_ROLE]
      iap_role_check.require_all = False
      self.add_child(iap_role_check)


class OsLoginStatusCheck(runbook.Gateway):
  """Checks for OS Login setup and and non OS login setup on a VM to guide further diagnostics.

  If using OS Login investigates OS Login related configuration and permission and if not
  Checks Keybased Configuration.
  """

  def execute(self):
    """Identifying OS Login Setup."""
    # User intends to use OS login
    if op.get(flags.CHECK_OS_LOGIN):
      os_login_check = gce_gs.VmMetadataCheck()
      os_login_check.template = 'vm_metadata::os_login_enabled'
      os_login_check.metadata_key = 'enable-oslogin'
      os_login_check.expected_value = True
      self.add_child(os_login_check)

      os_login_role_check = iam_gs.IamPolicyCheck()
      os_login_role_check.template = 'gcpdiag.runbook.gce::permissions::has_os_login'
      os_login_role_check.roles = [
          gce_const.OSLOGIN_ROLE, gce_const.OSLOGIN_ADMIN_ROLE,
          gce_const.OWNER_ROLE
      ]
      os_login_role_check.require_all = False
      self.add_child(os_login_role_check)
      sa_user_role_check = iam_gs.IamPolicyCheck()
      sa_user_role_check.template = 'gcpdiag.runbook.gce::permissions::sa_user_role'
      sa_user_role_check.roles = [gce_const.SA_USER_ROLE]
      sa_user_role_check.require_all = False
      self.add_child(sa_user_role_check)

      if not op.get(flags.CHECK_OS_LOGIN):
        metadata_perm_check = iam_gs.IamPolicyCheck()
        metadata_perm_check.template = 'gcpdiag.runbook.gce::permissions::can_set_metadata'
        metadata_perm_check.permissions = [
            'compute.instances.setMetadata',
            'compute.projects.setCommonInstanceMetadata'
        ]
        metadata_perm_check.require_all = False
        self.add_child(metadata_perm_check)
        os_login_check = gce_gs.VmMetadataCheck()
        os_login_check.template = 'vm_metadata::no_os_login'
        os_login_check.metadata_key = 'enable_oslogin'
        os_login_check.expected_value = False
        self.add_child(os_login_check)
        self.add_child(PoxisUserHasValidSshKeyCheck())


class PoxisUserHasValidSshKeyCheck(runbook.Step):
  """Verifies the existence of a valid SSH key for the specified local Proxy user on a (VM).

  Ensures that the local user has at least one valid SSH key configured in the VM's metadata, which
  is essential for secure SSH access. The check is performed against the SSH keys stored within
  the VM's metadata. A successful verification indicates that the user is likely able to SSH into
  the VM using their key.
  """

  template = 'vm_metadata::valid_ssh_key'

  def execute(self):
    """Validating SSH key for local user..."""

    vm = gce.get_instance(project_id=op.get(flags.PROJECT_ID),
                          zone=op.get(flags.ZONE),
                          instance_name=op.get(flags.NAME))

    # Check if the local_user has a valid key in the VM's metadata.
    ssh_keys = vm.get_metadata('ssh-keys').split('\n') if vm.get_metadata(
        'ssh-keys') else []
    has_valid_key = util.user_has_valid_ssh_key(op.get(flags.LOCAL_USER),
                                                ssh_keys)
    if has_valid_key:
      op.add_ok(resource=vm,
                reason=op.prep_msg(op.SUCCESS_REASON,
                                   local_user=op.get(flags.LOCAL_USER),
                                   vm_name=vm.name))
    else:
      op.add_failed(vm,
                    reason=op.prep_msg(op.FAILURE_REASON,
                                       local_user=op.get(flags.LOCAL_USER),
                                       vm_name=vm.name),
                    remediation=op.prep_msg(op.FAILURE_REMEDIATION,
                                            local_user=op.get(
                                                flags.LOCAL_USER)))


class GceFirewallAllowsSsh(runbook.Gateway):
  """Assesses the VPC network configuration to ensure it allows SSH traffic to the target VM.

  This diagnostic step checks for ingress firewall rules that permit SSH traffic based on
  the operational context, such as the use of IAP for SSH or direct access from a specified
  source IP. It helps identify network configurations that might block SSH connections."""

  def execute(self):
    """Evaluating VPC network firewall rules for SSH access..."""
    vm = gce.get_instance(project_id=op.get(flags.PROJECT_ID),
                          zone=op.get(flags.ZONE),
                          instance_name=op.get(flags.NAME))

    if op.get(flags.TUNNEL_THROUGH_IAP):
      tti_ingress_check = gce_gs.GceVpcConnectivityCheck()
      tti_ingress_check.traffic = 'ingress'
      # Check IAP Firewall rule if specified
      tti_ingress_check.template = 'vpc_connectivity::tti_ingress'
      self.add_child(tti_ingress_check)
    if (not op.get(flags.SRC_IP) and not op.get(flags.TUNNEL_THROUGH_IAP) and
        vm.is_public_machine()):
      default_ingress_check = gce_gs.GceVpcConnectivityCheck()
      default_ingress_check.traffic = 'ingress'
      default_ingress_check.template = 'vpc_connectivity::default_ingress'

      self.add_child(default_ingress_check)

    # Check provided source IP has access
    if op.get(flags.SRC_IP) and not op.get(flags.TUNNEL_THROUGH_IAP):
      custom_ip_ingress_check = gce_gs.GceVpcConnectivityCheck()
      custom_ip_ingress_check.traffic = 'ingress'
      custom_ip_ingress_check.template = 'vpc_connectivity::default_ingress'
      self.add_child(custom_ip_ingress_check)


class VmPerformanceChecks(runbook.CompositeStep):
  """Assesses the overall performance of a VM by evaluating its memory, CPU, and disk utilization.

  This composite diagnostic step sequentially checks for high memory utilization, high disk
  utilization, and CPU performance issues. It adds specific child steps designed to identify and
  report potential performance bottlenecks that could impact the VM's operation and efficiency.
  """

  def execute(self):
    """Evaluating VM memory, CPU, and disk performance..."""
    self.add_child(child=gce_gs.HighVmMemoryUtilization())
    self.add_child(child=gce_gs.HighVmDiskUtilization())
    self.add_child(child=gce_gs.HighVmCpuUtilization())


class LinuxGuestOsChecks(runbook.CompositeStep):
  """Examines Linux-based guest OS's serial log entries for guest os level issues.

  This composite step scrutinizes the VM's serial logs for patterns indicative of kernel panics,
  problems with the SSH daemon, and blocks by SSH Guard - each of which could signify underlying
  issues affecting the VM's stability and accessibility. By identifying these specific patterns,
  the step aims to isolate common Linux OS and application issues, facilitating targeted
  troubleshooting.
  """

  def execute(self):
    """Analyzing serial logs for common linux guest os and application issues..."""
    # Check for kernel panic patterns in serial logs.
    kernel_panic = gce_gs.VmSerialLogsCheck()
    kernel_panic.template = 'vm_serial_log::kernel_panic'
    kernel_panic.negative_pattern = gce_const.KERNEL_PANIC_LOGS
    kernel_panic.positive_pattern = ['systemd', 'OSConfigAgent']

    self.add_child(kernel_panic)
    # Check for issues in SSHD configuration or behavior.
    sshd_check = gce_gs.VmSerialLogsCheck()
    sshd_check.template = 'vm_serial_log::sshd'
    sshd_check.negative_pattern = gce_const.BAD_SSHD_PATTERNS
    sshd_check.positive_pattern = gce_const.GOOD_SSHD_PATTERNS
    self.add_child(sshd_check)
    # Check for SSH Guard blocks that might be preventing SSH access.
    sshd_guard = gce_gs.VmSerialLogsCheck()
    sshd_guard.template = 'vm_serial_log::sshguard'
    sshd_guard.negative_pattern = gce_const.SSHGUARD_PATTERNS
    self.add_child(sshd_guard)


class WindowsGuestOsChecks(runbook.CompositeStep):
  """Diagnoses common issues related to Windows Guest OS, focusing on boot-up processes and SSHD.

  This composite diagnostic step evaluates the VM's metadata to ensure SSH is enabled for Windows,
  checks serial logs for successful boot-up patterns, and involves a manual check on the Windows SSH
  agent status. It aims to identify and help troubleshoot potential issues that could impact the
  VM's accessibility via SSHD.
  """

  def execute(self):
    """Analyzing Windows Guest OS boot-up and SSH agent status..."""
    # Check Windows Metadata enabling ssh is set as this is required for windows
    windows_ssh_md = gce_gs.VmMetadataCheck()
    windows_ssh_md.template = 'vm_metadata::windows_ssh_md'
    windows_ssh_md.metadata_key = 'enable-windows-ssh'
    windows_ssh_md.expected_value = True
    self.add_child(windows_ssh_md)

    windows_good_bootup = gce_gs.VmSerialLogsCheck()
    windows_good_bootup.template = 'vm_serial_log::windows_bootup'
    windows_good_bootup.positive_pattern = gce_const.GOOD_WINDOWS_BOOT_LOGS_READY
    self.add_child(windows_good_bootup)

    check_windows_ssh_agent = gcp_gs.HumanTask()
    vm = gce.get_instance(project_id=op.get(flags.PROJECT_ID),
                          zone=op.get(flags.ZONE),
                          instance_name=op.get(flags.NAME))
    check_windows_ssh_agent.resource = vm
    check_windows_ssh_agent.template = 'gcpdiag.runbook.gce::vm_serial_log::windows_gce_ssh_agent'
    self.add_child(check_windows_ssh_agent)
