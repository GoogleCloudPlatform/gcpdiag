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
from gcpdiag.runbook.gce import constants as gce_const
from gcpdiag.runbook.gce import flags
from gcpdiag.runbook.gce import generalized_steps as gce_gs
from gcpdiag.runbook.gce import util
from gcpdiag.runbook.gcp import generalized_steps as platform_gs


class Ssh(runbook.DiagnosticTree):
  """Provides a comprehensive analysis of common issues which affects SSH connectivity to VMs.

  This runbook focuses on a range of potential problems for both Windows and Linux VMs on
  Google Cloud Platform. By conducting a series of checks, the runbook aims to pinpoint the
  root cause of SSH access difficulties.

  The following areas are examined:

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
    """
  # Specify parameters common to all steps in the diagnostic tree class.
  parameters = {
      flags.PROJECT_ID: {
          'type': str,
          'help': 'The ID of the project hosting the VM',
          'required': True
      },
      flags.NAME: {
          'type': str,
          'help': 'The name or instance ID of the target VM',
          'required': True
      },
      flags.ZONE: {
          'type': str,
          'help': 'The zone of the target VM',
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
          'type': ipaddress.IPv4Address,
          'help': (
              'Source IP address. Workstation connecting from workstation,'
              'Ip of the bastion/jumphost if currently on logged on a basition/jumphost '
          ),
          'default': gce_const.IAP_FW_VIP,
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
    project = crm.get_project(self.op.get(flags.PROJECT_ID))
    try:
      vm = gce.get_instance(project_id=self.op.get(flags.PROJECT_ID),
                            zone=self.op.get(flags.ZONE),
                            instance_name=self.op.get(flags.NAME))
    except googleapiclient.errors.HttpError:
      self.op.add_skipped(
          project,
          reason=('Instance {} does not exist in zone {} or project {}').format(
              self.op.get(flags.NAME), self.op.get(flags.ZONE),
              self.op.get(flags.PROJECT_ID)))
    else:
      if vm:
        # check if user supplied an instance id or a name.
        if self.op[flags.NAME].isdigit():
          self.op[flags.NAME] = vm.name
        # Perform basic parameter checks and parse
        # string boolean into boolean values
        if self.op.get(flags.CHECK_OS_LOGIN):
          self.op.info('Will check for OS login configuration')
        else:
          self.op.info('Will check for Metadata based SSH key configuration')

        if (not self.op.get(flags.SRC_IP) and
            not self.op.get(flags.TUNNEL_THROUGH_IAP) and
            vm.is_public_machine()):
          self.op[flags.SRC_IP] = gce_const.UNSPECIFIED_ADDRESS
        self.op.info('Checks will use ip {} as the source IP'.format(
            self.op.get(flags.SRC_IP)))
        if self.op.get(flags.TUNNEL_THROUGH_IAP):
          # set IAP VIP as the source to the VM
          self.op[flags.SRC_IP] = gce_const.IAP_FW_VIP
          self.op.info('Will check for IAP configuration')
        else:
          self.op.info(
              'Will not check for IAP for TCP forwarding configuration')
        if self.op.get(flags.LOCAL_USER):
          self.op[flags.LOCAL_USER] = self.op.get(flags.LOCAL_USER)
          self.op.info(
              f'Local User: {self.op.get(flags.LOCAL_USER)} will be used '
              f'examine metadata-based SSH Key configuration')
        if self.op.get(flags.PRINCIPAL):
          email_only = len(self.op.get(flags.PRINCIPAL).split(':')) == 1
          if email_only:
            # Get the type
            p_policy = iam.get_project_policy(vm.project_id)
            p_type = p_policy.get_member_type(self.op.get(flags.PRINCIPAL))
            self.op[
                flags.PRINCIPAL] = f'{p_type}:{self.op.get(flags.PRINCIPAL)}'
            if p_type:
              self.op.info(
                  f'Checks will use {self.op.get(flags.PRINCIPAL)} as the authenticated\n'
                  'principal in Cloud Console / gcloud (incl. impersonated service account)'
              )
            else:
              # groups and org principals are not expanded.
              # prompt until groups and inherited principals expanded
              # for projects.
              pass
        # Set IP protocol
        self.op[flags.PROTOCOL_TYPE] = 'tcp'
        if not self.op.get(flags.PORT):
          self.op[flags.PORT] = gce_const.DEFAULT_SSHD_PORT

    ops_agent_q = monitoring.query(
        self.op.get(flags.PROJECT_ID), """
              fetch gce_instance
              | metric 'agent.googleapis.com/agent/uptime'
              | filter (metadata.system_labels.name == '{}')
              | align rate(5m)
              | every 5m
              | {}
            """.format(self.op.get(flags.NAME), gce_gs.within_str))
    if ops_agent_q:
      self.op.info('Will use ops agent metrics for relevant assessments')
      self.op[flags.OPS_AGENT_EXPORTING_METRICS] = True


class VmGuestOsType(runbook.Gateway):
  """Distinguishes between Windows and Linux operating systems on a VM to guide further diagnostics.

  Based on the OS type, it directs the diagnostic process towards OS-specific checks,
  ensuring relevancy and efficiency in troubleshooting efforts.
  """

  def execute(self):
    """Identifying Guest OS type..."""
    vm = gce.get_instance(project_id=self.op.get(flags.PROJECT_ID),
                          zone=self.op.get(flags.ZONE),
                          instance_name=self.op.get(flags.NAME))
    if not vm.is_windows_machine():
      self.op.info(
          'Detected Linux VM. Proceeding with Linux-specific diagnostics.')
      self.add_child(LinuxGuestOsChecks())
    else:
      self.op.info(
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
      response = self.op.prompt(
          step=self.op.interface.output.CONFIRMATION,
          message=f'Are you able to SSH into VM {self.op.get(flags.NAME)}?')
      if response == self.op.interface.output.NO:
        self.op.info(message=gce_const.END_MESSAGE)


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
    self.add_child(gce_gs.AuthPrincipalCloudConsolePermissionCheck())
    # Both OS login and gcloud key based require this.
    self.add_child(AuthPrincipalHasPermissionToFetchVmCheck())
    # Check OS login or Key based auth preference.
    self.add_child(OsLoginStatusCheck())

    if self.op.get(flags.TUNNEL_THROUGH_IAP):
      self.add_child(AuthPrincipalHasIapTunnelUserPermissionsCheck())


class OsLoginStatusCheck(runbook.Gateway):
  """Checks for OS Login setup and and non OS login setup on a VM to guide further diagnostics.

  If using OS Login investiages OS Login related configuration and permission and if not
  Checks Keybased Configuration.
  """

  def execute(self):
    """Identifying OS Login Setup."""
    # User intends to use OS login
    if self.op.get(flags.CHECK_OS_LOGIN):
      self.op.info(
          'OS login setup is desired, Hence OS login related configurations')
      os_login_check = gce_gs.VmMetadataCheck()
      os_login_check.template = 'vm_metadata::os_login_enabled'
      os_login_check.metadata_key = 'enable-oslogin'
      os_login_check.expected_value = True
      self.add_child(os_login_check)
      self.add_child(AuthPrincipalHasOsLoginPermissionsCheck())
      self.add_child(AuthPrincipalHasServiceAccountUserCheck())

      if not self.op.get(flags.CHECK_OS_LOGIN):
        self.op.info(
            'Key Based ssh authentication desired, Hence investing Key based SSH configuration.'
        )
        self.add_child(AuthPrincipalHasComputeMetadataPermissionsCheck())
        os_login_check = gce_gs.VmMetadataCheck()
        os_login_check.template = 'vm_metadata::no_os_login'
        os_login_check.metadata_key = 'enable_oslogin'
        os_login_check.expected_value = False
        self.add_child(os_login_check)
        self.add_child(PoxisUserHasValidSshKeyCheck())


class AuthPrincipalHasComputeMetadataPermissionsCheck(runbook.Step):
  """Verifies if the authenticated user has permissions to update SSH metadata.

  This step checks if the user has the necessary permissions to modify SSH metadata at
  the project or instance level. It focuses on project-level permissions and does not consider
  permissions inherited from ancestor resources like folders or organizations.
  """
  template = 'gce_permissions::can_set_metadata'

  metadata_permissions = [
      'compute.instances.setMetadata',
      'compute.projects.setCommonInstanceMetadata'
  ]

  def execute(self):
    """Verifying SSH metadata update permissions..."""

    iam_policy = iam.get_project_policy(self.op.get(flags.PROJECT_ID))

    auth_user = self.op.get(flags.PRINCIPAL)
    can_set_metadata = iam_policy.has_any_permission(auth_user,
                                                     self.metadata_permissions)
    if can_set_metadata:
      self.op.add_ok(resource=iam_policy,
                     reason=self.op.get_msg(gce_const.SUCCESS_REASON,
                                            auth_user=auth_user))
    else:
      self.op.add_failed(iam_policy,
                         reason=self.op.get_msg(
                             gce_const.FAILURE_REASON,
                             metadata_permissions=self.metadata_permissions),
                         remediation=self.op.get_msg(
                             gce_const.FAILURE_REMEDIATION))


class AuthPrincipalHasPermissionToFetchVmCheck(runbook.Step):
  """Validates if a user has the necessary permissions to retrieve information about a GCE instance.

  This step checks for specific permissions related to instance retrieval.
  It is critical for ensuring that the user executing the SSH command with gcloud or console has
  the ability to access detailed information about the instance in question."""

  # Instance related permissions variables
  instance_permissions = ['compute.instances.get', 'compute.instances.use']

  template = 'gce_permissions::instances_get'

  def execute(self):
    """Verifying instance retrieval permissions..."""

    iam_policy = iam.get_project_policy(self.op.get(flags.PROJECT_ID))

    auth_user = self.op.get(flags.PRINCIPAL)
    if iam_policy.has_any_permission(auth_user, self.instance_permissions):
      self.op.add_ok(resource=iam_policy,
                     reason=self.op.get_msg(gce_const.SUCCESS_REASON,
                                            auth_user=auth_user))
    else:
      self.op.add_failed(iam_policy,
                         reason=self.op.get_msg(
                             gce_const.FAILURE_REASON,
                             auth_user=auth_user,
                             instance_permissions=self.instance_permissions),
                         remediation=self.op.get_msg(
                             gce_const.FAILURE_REMEDIATION,
                             auth_user=auth_user,
                             instance_permissions=self.instance_permissions))


class PoxisUserHasValidSshKeyCheck(runbook.Step):
  """Verifies the existence of a valid SSH key for the specified local Poxis user on a (VM).

  Ensures that the local user has at least one valid SSH key configured in the VM's metadata, which
  is essential for secure SSH access. The check is performed against the SSH keys stored within
  the VM's metadata. A successful verification indicates that the user is likely able to SSH into
  the VM using their key.
  """

  template = 'vm_metadata::valid_ssh_key'

  def execute(self):
    """Validating SSH key for local user..."""

    vm = gce.get_instance(project_id=self.op.get(flags.PROJECT_ID),
                          zone=self.op.get(flags.ZONE),
                          instance_name=self.op.get(flags.NAME))

    # Check if the local_user has a valid key in the VM's metadata.
    ssh_keys = vm.get_metadata('ssh-keys').split('\n') if vm.get_metadata(
        'ssh-keys') else []
    has_valid_key = util.user_has_valid_ssh_key(self.op.get(flags.LOCAL_USER),
                                                ssh_keys)
    if has_valid_key:
      self.op.add_ok(resource=vm,
                     reason=self.op.get_msg(gce_const.SUCCESS_REASON,
                                            local_user=self.op.get(
                                                flags.LOCAL_USER),
                                            vm_name=vm.name))
    else:
      self.op.add_failed(
          vm,
          reason=self.op.get_msg(gce_const.FAILURE_REASON,
                                 local_user=self.op.get(flags.LOCAL_USER),
                                 vm_name=vm.name),
          remediation=self.op.get_msg(gce_const.FAILURE_REMEDIATION,
                                      local_user=self.op.get(flags.LOCAL_USER)))


class AuthPrincipalHasOsLoginPermissionsCheck(runbook.Step):
  """Evaluates whether the user has the necessary IAM roles to use OS Login access a GCE instance.

  This step ensures the user possesses one of the required roles: OS Login User, OS Login Admin,
  or Project Owner, which are essential for accessing instances via the OS Login feature.
  A failure indicates the need to adjust IAM policies.
  """
  template = 'gce_permissions::has_os_login'

  def execute(self):
    """Evaluating OS Login permissions for the user..."""

    vm = gce.get_instance(project_id=self.op.get(flags.PROJECT_ID),
                          zone=self.op.get(flags.ZONE),
                          instance_name=self.op.get(flags.NAME))
    iam_policy = iam.get_project_policy(self.op.get(flags.PROJECT_ID))

    auth_user = self.op.get(flags.PRINCIPAL)

    # Does the instance have a service account?
    # Then users needs to have permissions to user the service account
    if not (iam_policy.has_role_permissions(
        auth_user, gce_const.OSLOGIN_ROLE) or iam_policy.has_role_permissions(
            auth_user, gce_const.OSLOGIN_ADMIN_ROLE) or
            iam_policy.has_role_permissions(auth_user, gce_const.OWNER_ROLE)):
      self.op.add_failed(iam_policy,
                         reason=self.op.get_msg(
                             gce_const.FAILURE_REASON,
                             auth_user=auth_user,
                             os_login_role=gce_const.OSLOGIN_ROLE,
                             os_login_admin_role=gce_const.OSLOGIN_ADMIN_ROLE,
                             owner_role=gce_const.OWNER_ROLE),
                         remediation=self.op.get_msg(
                             gce_const.FAILURE_REMEDIATION,
                             auth_user=auth_user,
                             os_login_role=gce_const.OSLOGIN_ROLE,
                             os_login_admin_role=gce_const.OSLOGIN_ADMIN_ROLE))
    else:
      self.op.add_ok(resource=vm,
                     reason=self.op.get_msg(
                         gce_const.SUCCESS_REASON,
                         auth_user=auth_user,
                         os_login_role=gce_const.OSLOGIN_ROLE,
                         os_login_admin_role=gce_const.OSLOGIN_ADMIN_ROLE,
                         owner_role=gce_const.OWNER_ROLE))


class AuthPrincipalHasServiceAccountUserCheck(runbook.Step):
  """Verifies if the user has the 'Service Account User' role for a VM's attached service account.

  This step is crucial for scenarios where a VM utilizes a service account for various operations.
  It ensures the user performing the diagnostics has adequate permissions to use the service account
  attached to the specified VM. Note: This check focuses on project-level roles and does not account
  for permissions inherited from higher-level resources such as folders or organizations.
  """
  template = 'gce_permissions::sa_user_role'

  def execute(self):
    """Evaluating user permissions for the service account..."""

    vm = gce.get_instance(project_id=self.op.get(flags.PROJECT_ID),
                          zone=self.op.get(flags.ZONE),
                          instance_name=self.op.get(flags.NAME))
    iam_policy = iam.get_project_policy(vm.project_id)

    auth_user = self.op.get(flags.PRINCIPAL)

    if vm.service_account:
      if not iam_policy.has_role_permissions(auth_user, gce_const.SA_USER_ROLE):
        self.op.add_failed(
            vm,
            reason=self.op.get_msg(gce_const.FAILURE_REASON,
                                   auth_user=auth_user,
                                   sa_user_role=gce_const.SA_USER_ROLE,
                                   service_account=vm.service_account),
            remediation=self.op.get_msg(gce_const.FAILURE_REMEDIATION,
                                        auth_user=auth_user,
                                        sa_user_role=gce_const.SA_USER_ROLE))
      else:
        self.op.add_ok(resource=vm,
                       reason=self.op.get_msg(
                           gce_const.SUCCESS_REASON,
                           auth_user=auth_user,
                           sa_user_role=gce_const.SA_USER_ROLE,
                           service_account=vm.service_account))


class AuthPrincipalHasIapTunnelUserPermissionsCheck(runbook.Step):
  """Verifies if the authenticated user has the required IAP roles to establish a tunnel to a VM.

  This step examines scenarios where users need to tunnel into a VM via IAP. It checks if the
  user has the 'roles/iap.tunnelResourceAccessor' role at the project level, necessary for
  initiating an Identity-Aware Proxy tunnel. The check focuses on project-level roles, not
  considering more granular permissions that might be assigned directly to the VM or inherited
  from higher-level resources.
  """
  template = 'gce_permissions::iap_role'

  def execute(self):
    """Evaluating IAP Tunnel user permissions..."""

    vm = gce.get_instance(project_id=self.op.get(flags.PROJECT_ID),
                          zone=self.op.get(flags.ZONE),
                          instance_name=self.op.get(flags.NAME))
    iam_policy = iam.get_project_policy(self.op.get(flags.PROJECT_ID))

    auth_user = self.op.get(flags.PRINCIPAL)
    # Check for IAP config
    # TODO improve this to check that it affects the
    #  interested instance. because IAP and Service account roles can be scoped to VM
    if auth_user and not iam_policy.has_role_permissions(
        f'{auth_user}', gce_const.IAP_ROLE):
      self.op.add_failed(iam_policy,
                         reason=self.op.get_msg(gce_const.FAILURE_REASON,
                                                auth_user=auth_user,
                                                iap_role=gce_const.IAP_ROLE),
                         remediation=self.op.get_msg(
                             gce_const.FAILURE_REMEDIATION,
                             auth_user=auth_user,
                             iap_role=gce_const.IAP_ROLE))
    else:
      self.op.add_ok(resource=vm,
                     reason=self.op.get_msg(gce_const.SUCCESS_REASON,
                                            auth_user=auth_user,
                                            iap_role=gce_const.IAP_ROLE))


class GceFirewallAllowsSsh(runbook.CompositeStep):
  """Assesses the VPC network configuration to ensure it allows SSH traffic to the target VM.

  This diagnostic step checks for ingress firewall rules that permit SSH traffic based on
  the operational context, such as the use of IAP for SSH or direct access from a specified
  source IP. It helps identify network configurations that might block SSH connections."""

  def execute(self):
    """Evaluating VPC network firewall rules for SSH access..."""
    vm = gce.get_instance(project_id=self.op.get(flags.PROJECT_ID),
                          zone=self.op.get(flags.ZONE),
                          instance_name=self.op.get(flags.NAME))

    if self.op.get(flags.TUNNEL_THROUGH_IAP):
      tti_ingress_check = gce_gs.GceVpcConnectivityCheck()
      tti_ingress_check.traffic = 'ingress'
      # Check IAP Firewall rule if specified
      tti_ingress_check.template = 'vpc_connectivity::tti_ingress'
      self.add_child(tti_ingress_check)
    if (not self.op.get(flags.SRC_IP) and
        not self.op.get(flags.TUNNEL_THROUGH_IAP) and vm.is_public_machine()):
      default_ingress_check = gce_gs.GceVpcConnectivityCheck()
      default_ingress_check.traffic = 'ingress'
      default_ingress_check.template = 'vpc_connectivity::default_ingress'

      self.add_child(default_ingress_check)

    # Check provided source IP has access
    if self.op.get(flags.SRC_IP) and not self.op.get(flags.TUNNEL_THROUGH_IAP):
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
  VM's accessibility via SSHD
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

    check_windows_ssh_agent = platform_gs.HumanTask()
    vm = gce.get_instance(project_id=self.op.get(flags.PROJECT_ID),
                          zone=self.op.get(flags.ZONE),
                          instance_name=self.op.get(flags.NAME))
    check_windows_ssh_agent.resource = vm
    check_windows_ssh_agent.prompts[gce_const.INSTRUCTIONS_CHOICE_OPTIONS] = {
        'y': 'Yes',
        'n': 'No',
        'u': 'Unsure'
    }
    check_windows_ssh_agent.template = 'gcpdiag.runbook.gce::vm_serial_log::windows_gce_ssh_agent'
    self.add_child(check_windows_ssh_agent)
