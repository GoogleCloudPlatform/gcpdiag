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
from ipaddress import IPv4Address

import googleapiclient.errors

from gcpdiag import config, runbook
from gcpdiag.queries import crm, gce, iam
from gcpdiag.runbook import op
from gcpdiag.runbook.crm import generalized_steps as crm_gs
from gcpdiag.runbook.gce import constants as gce_const
from gcpdiag.runbook.gce import flags
from gcpdiag.runbook.gce import generalized_steps as gce_gs
from gcpdiag.runbook.gce import util
from gcpdiag.runbook.gcp import generalized_steps as gcp_gs
from gcpdiag.runbook.iam import generalized_steps as iam_gs

CHECK_SSH_IN_BROWSER = 'check_ssh_in_browser'
CLIENT = 'client'
ACCESS_METHOD = 'access_method'
MFA = 'mfa'
IAP = 'iap'
OSLOGIN = 'oslogin'
SSH_KEY_IN_METADATA = 'ssh-key-in-metadata'
SSH_IN_BROWSER = 'ssh-in-browser'
OSLOGIN_2FA = 'oslogin-2fa'
SECURITY_KEY = 'security-key'
OPENSSH = 'openssh'
GCLOUD = 'gcloud'
PUTTY = 'putty'
IAP_DESKTOP = 'iap-desktop'
JUMPHOST = 'jumphost'


class Ssh(runbook.DiagnosticTree):
  """A comprehensive troubleshooting guide for common issues which affects SSH connectivity to VMs.

  Investigates components required for ssh on either Windows and Linux VMs
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
          'help': 'The ID of the project hosting the GCE Instance',
          'required': True
      },
      flags.NAME: {
          'type': str,
          'help': 'The name of the target GCE Instance',
          'deprecated': True,
          'new_parameter': 'instance_name',
          'group': 'instance'
      },
      flags.INSTANCE_NAME: {
          'type': str,
          'help': 'The name of the target GCE Instance',
          'group': 'instance'
      },
      flags.INSTANCE_ID: {
          'type': int,
          'help': 'The instance ID of the target GCE Instance',
          'group': 'instance'
      },
      flags.ID: {
          'type': int,
          'help': 'The instance ID of the target GCE Instance',
          'group': 'instance'
      },
      flags.ZONE: {
          'type': str,
          'help': 'The zone of the target GCE Instance',
          'required': True
      },
      flags.PRINCIPAL: {
          'type': str,
          'help': (
              'The user or service account initiating '
              'the SSH connection. This user should be authenticated in '
              'gcloud/cloud console when sshing into to a GCE instance. '
              'For service account impersonation, it should be the '
              'service account\'s email. (format: user:user@example.com or '
              'serviceAccount:service-account-name@project-id.iam.gserviceaccount.com)'
          ),
          'ignorecase': True
      },
      flags.LOCAL_USER: {
          'type': str,
          'help': 'Posix User on the VM',
          'deprecated': True,
          'new_parameter': 'posix_user'
      },
      flags.POSIX_USER: {
          'type': str,
          'help': 'Posix User on the VM',
      },
      flags.TUNNEL_THROUGH_IAP: {
          'type': bool,
          'help':
              ('A boolean parameter (true or false) indicating whether ',
               'Identity-Aware Proxy should be used for establishing the SSH '
               'connection.'),
          'default': True,
          'deprecated': True,
          'new_parameter': 'proxy'
      },
      flags.PROXY: {
          'type': str,
          'help': (
              'A string that specifies the method used to establish the SSH connection, ',
              'and indicating whether Identity-Aware Proxy (IAP) or a jumphost is utilized.'
          ),
          'enum': ['iap', 'jumphost']
      },
      flags.CHECK_OS_LOGIN: {
          'type': bool,
          'help': ('A boolean value (true or false) indicating whether OS '
                   'Login should be used for SSH authentication'),
          'default': True,
          'deprecated': True,
          'new_parameter': 'access_method'
      },
      flags.CLIENT: {
          'type':
              str,
          'help':
              'The SSH client application used to establish SSH connection',
          'enum': [
              'ssh-in-browser', 'gcloud', 'openssh', 'putty', 'iap-desktop'
          ]
      },
      flags.SRC_IP: {
          'type':
              IPv4Address,
          'help': (
              'The IPv4 address of the workstation connecting to the network, '
              'or the IP of the bastion/jumphost if currently logged in through one.'
          )
      },
      flags.PROTOCOL_TYPE: {
          'type': str,
          'help': 'Protocol used to connect to SSH',
          'default': 'tcp',
          'deprecated': True
      },
      flags.PORT: {
          'type':
              int,
          'help':
              'The port used to connect to on the remote host (default: 22)',
          'default':
              gce_const.DEFAULT_SSHD_PORT
      },
      CHECK_SSH_IN_BROWSER: {
          'type': bool,
          'help': 'Check that SSH in Browser is feasible',
          'default': False,
          'deprecated': True,
          'new_parameter': 'client'
      },
      ACCESS_METHOD: {
          'type': str,
          'help': 'The method used to share or restrict access to the instance',
          'enum': ['oslogin', 'ssh-key-in-metadata']
      },
      MFA: {
          'type':
              str,
          'help':
              'Multifactor authentication required to access to the instance',
          'enum': ['oslogin-2fa', 'security-key']
      }
  }

  def legacy_parameter_handler(self, parameters):
    if flags.NAME in parameters:
      parameters[flags.INSTANCE_NAME] = parameters.pop(flags.NAME)

    if flags.ID in parameters:
      parameters[flags.INSTANCE_ID] = parameters.pop(flags.ID)

    if flags.LOCAL_USER in parameters:
      parameters[flags.POSIX_USER] = parameters.pop(flags.LOCAL_USER)

    if flags.TUNNEL_THROUGH_IAP in parameters:
      parameters[flags.PROXY] = IAP
      del parameters[flags.TUNNEL_THROUGH_IAP]

    if flags.CHECK_OS_LOGIN in parameters:
      parameters[flags.ACCESS_METHOD] = OSLOGIN
      del parameters[flags.CHECK_OS_LOGIN]

    if CHECK_SSH_IN_BROWSER in parameters:
      if parameters.pop(CHECK_SSH_IN_BROWSER):
        parameters[flags.CLIENT] = SSH_IN_BROWSER

    if flags.PROTOCOL_TYPE in parameters:
      del parameters[flags.PROTOCOL_TYPE]  # Deprecated with no replacement

  def build_tree(self):
    start = SshStart()
    lifecycle_check = gce_gs.VmLifecycleState()
    lifecycle_check.project_id = op.get(flags.PROJECT_ID)
    lifecycle_check.zone = op.get(flags.ZONE)
    lifecycle_check.instance_name = op.get(flags.INSTANCE_NAME)
    lifecycle_check.expected_lifecycle_status = 'RUNNING'
    performance_check = VmPerformanceChecks()
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
    if op.get(flags.PRINCIPAL):
      gce_permission_check = GcpSshPermissions()
      self.add_step(parent=start, child=gce_permission_check)
    self.add_step(parent=start, child=gce_firewall_check)

    # Check for Guest Agent status
    guest_agent_check = gce_gs.VmSerialLogsCheck()
    guest_agent_check.project_id = op.get(flags.PROJECT_ID)
    guest_agent_check.zone = op.get(flags.ZONE)
    guest_agent_check.instance_name = op.get(flags.INSTANCE_NAME)
    guest_agent_check.template = 'vm_serial_log::guest_agent'
    guest_agent_check.positive_pattern = gce_const.GUEST_AGENT_STATUS_MSG
    guest_agent_check.negative_pattern = gce_const.GUEST_AGENT_FAILED_MSG
    self.add_step(parent=start, child=guest_agent_check)

    # Check for SSH issues due to bad permissions
    sshd_auth_failure = gce_gs.VmSerialLogsCheck()
    sshd_auth_failure.project_id = op.get(flags.PROJECT_ID)
    sshd_auth_failure.zone = op.get(flags.ZONE)
    sshd_auth_failure.instance_name = op.get(flags.INSTANCE_NAME)
    sshd_auth_failure.template = 'vm_serial_log::sshd_auth_failure'
    sshd_auth_failure.negative_pattern = gce_const.SSHD_AUTH_FAILURE
    self.add_step(parent=start, child=sshd_auth_failure)

    # users wants to use SSH in Browser
    if op.get(CLIENT) == SSH_IN_BROWSER:
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
                            instance_name=op.get(flags.INSTANCE_NAME))
    except googleapiclient.errors.HttpError:
      op.add_skipped(
          project,
          reason=('Instance {} does not exist in zone {} or project {}').format(
              op.get(flags.INSTANCE_NAME), op.get(flags.ZONE),
              op.get(flags.PROJECT_ID)))
    else:
      if vm:
        # Check for instance id and instance name
        if not op.get(flags.ID):
          op.put(flags.ID, vm.id)
        elif not op.get(flags.INSTANCE_NAME):
          op.put(flags.INSTANCE_NAME, vm.name)
        # Align with the user on parameters to be investigated
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
                  f'GCP permissions related to SSH will be verified for: {op.get(flags.PRINCIPAL)}'
              )
        if not op.get(flags.SRC_IP) and not op.get(
            flags.PROXY) and vm.is_public_machine():
          op.put(flags.SRC_IP, gce_const.UNSPECIFIED_ADDRESS)
          op.info(
              f'No proxy specified. Setting source IP range to: {gce_const.UNSPECIFIED_ADDRESS}'
          )
        if op.get(flags.PROXY) == IAP:
          # set IAP VIP as the source to the VM
          op.put(flags.SRC_IP, gce_const.IAP_FW_VIP)
          op.info(
              f'Source IP to be used for SSH connectivity test: {op.get(flags.SRC_IP)}'
          )
        elif op.get(flags.PROXY) == JUMPHOST:
          op.info(
              f'Source IP to be used for SSH connectivity test: {op.get(flags.SRC_IP)}'
          )

        op.info(
            f'Port {op.get(flags.PORT)} and ip {op.get(flags.SRC_IP)} as the source IP'
        )

        if not op.get(flags.PORT):
          op.info(f'SSH port to investigate: {op.get(flags.PORT)}')

        if op.get(flags.ACCESS_METHOD) == OSLOGIN:
          op.info(
              'Access method to investigate: OS login https://cloud.google.com/compute/docs/oslogin'
          )
        elif op.get(flags.ACCESS_METHOD) == SSH_KEY_IN_METADATA:
          op.info(
              'Access method to investigate: SSH keys in metadata '
              'https://cloud.google.com/compute/docs/instances/access-overview#ssh-access'
          )

        if op.get(flags.POSIX_USER):
          op.info(
              f'Guest OS Posix User to be investigated: {op.get(flags.POSIX_USER)}'
          )
        if op.get(CLIENT) == SSH_IN_BROWSER:
          op.info('SSH Client to be investigated: SSH in Browser')
        if op.get(CLIENT) == GCLOUD:
          op.info('Investigating components required to use gcloud compute ssh')
        if op.get(CLIENT) in (IAP_DESKTOP, PUTTY, OPENSSH):
          op.info(
              'IAP Desktop, Putty and vanilla openssh investigations are not supported yet'
          )
        if op.get(MFA) == OSLOGIN_2FA:
          op.info(
              'Multifactor authentication to investigate: OS Login 2FA '
              'https://cloud.google.com/compute/docs/oslogin/set-up-oslogin#byb'
          )
        if op.get(MFA) == SECURITY_KEY:
          op.info(
              'Multifactor authentication to investigate: Security keys with OS Login  '
              'https://cloud.google.com/compute/docs/oslogin/security-keys')


class VmGuestOsType(runbook.Gateway):
  """Distinguishes between Windows and Linux operating systems on a VM to guide further diagnostics.

  Based on the OS type, it directs the diagnostic process towards OS-specific checks,
  ensuring relevancy and efficiency in troubleshooting efforts.
  """

  def execute(self):
    """Identify Guest OS type."""
    vm = gce.get_instance(project_id=op.get(flags.PROJECT_ID),
                          zone=op.get(flags.ZONE),
                          instance_name=op.get(flags.INSTANCE_NAME))
    if not vm.is_windows_machine():
      op.info(
          'Linux Guest OS detected. Proceeding with diagnostics specific to Linux systems.'
      )
      self.add_child(LinuxGuestOsChecks())
    else:
      op.info(
          'Windows Guest OS detected. Proceeding with diagnostics specific to Windows systems.'
      )
      self.add_child(WindowsGuestOsChecks())


class SshEnd(runbook.EndStep):
  """Concludes the SSH diagnostics process, offering guidance based on the user's feedback.

  If SSH issues persist, it directs the user to helpful resources and
  suggests contacting support with a detailed report
  """

  def execute(self):
    """Finalize SSH diagnostics."""
    if not config.get(flags.INTERACTIVE_MODE):
      response = op.prompt(
          kind=op.CONFIRMATION,
          message=f'Are you able to SSH into VM {op.get(flags.INSTANCE_NAME)}?',
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
    """Verify overall user permissions for SSH access.

    Note: Only roles granted at the project level are checked. Permissions inherited from
    ancestor resources such as folder(s) or organization and groups are not checked."""
    # Check user has permission to access the VM in the first place
    if op.get(CLIENT) == SSH_IN_BROWSER:
      console_permission = iam_gs.IamPolicyCheck()
      console_permission.project = op.get(flags.PROJECT_ID)
      console_permission.template = 'gcpdiag.runbook.gce::permissions::console_view_permission'
      console_permission.permissions = ['compute.projects.get']
      console_permission.principal = op.get(flags.PRINCIPAL)
      console_permission.require_all = False
      self.add_child(console_permission)
    # Both OS login and gcloud key based require this.
    instance_fetch_perm_check = iam_gs.IamPolicyCheck()
    instance_fetch_perm_check.project = op.get(flags.PROJECT_ID)
    instance_fetch_perm_check.principal = op.get(flags.PRINCIPAL)
    instance_fetch_perm_check.template = 'gcpdiag.runbook.gce::permissions::instances_get'
    instance_fetch_perm_check.permissions = ['compute.instances.get']
    instance_fetch_perm_check.require_all = False
    self.add_child(instance_fetch_perm_check)

    # Check OS login or Key based auth preference.
    self.add_child(OsLoginStatusCheck())

    if op.get(flags.PROXY) == IAP:
      iap_role_check = iam_gs.IamPolicyCheck()
      iap_role_check.project = op.get(flags.PROJECT_ID)
      iap_role_check.principal = op.get(flags.PRINCIPAL)
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
    """Identify OS Login Setup."""
    # User intends to use OS login
    if op.get(flags.ACCESS_METHOD) == OSLOGIN:
      os_login_check = gce_gs.VmMetadataCheck()
      os_login_check.project_id = op.get(flags.PROJECT_ID)
      os_login_check.zone = op.get(flags.ZONE)
      os_login_check.instance_name = op.get(flags.INSTANCE_NAME)
      os_login_check.template = 'vm_metadata::os_login_enabled'
      os_login_check.metadata_key = 'enable-oslogin'
      os_login_check.expected_value = True
      self.add_child(os_login_check)

      os_login_role_check = iam_gs.IamPolicyCheck()
      os_login_role_check.project = op.get(flags.PROJECT_ID)
      os_login_role_check.principal = op.get(flags.PRINCIPAL)
      os_login_role_check.template = 'gcpdiag.runbook.gce::permissions::has_os_login'
      os_login_role_check.roles = [
          gce_const.OSLOGIN_ROLE, gce_const.OSLOGIN_ADMIN_ROLE,
          gce_const.OWNER_ROLE
      ]
      os_login_role_check.require_all = False
      self.add_child(os_login_role_check)
      sa_user_role_check = iam_gs.IamPolicyCheck()
      sa_user_role_check.project = op.get(flags.PROJECT_ID)
      sa_user_role_check.principal = op.get(flags.PRINCIPAL)
      sa_user_role_check.template = 'gcpdiag.runbook.gce::permissions::sa_user_role'
      sa_user_role_check.roles = [gce_const.SA_USER_ROLE]
      sa_user_role_check.require_all = False
      self.add_child(sa_user_role_check)

    elif op.get(flags.ACCESS_METHOD) == SSH_KEY_IN_METADATA:
      metadata_perm_check = iam_gs.IamPolicyCheck()
      metadata_perm_check.project = op.get(flags.PROJECT_ID)
      metadata_perm_check.principal = op.get(flags.PRINCIPAL)
      metadata_perm_check.template = 'gcpdiag.runbook.gce::permissions::can_set_metadata'
      metadata_perm_check.permissions = [
          'compute.instances.setMetadata',
          'compute.projects.setCommonInstanceMetadata'
      ]
      metadata_perm_check.require_all = False
      self.add_child(metadata_perm_check)
      os_login_check = gce_gs.VmMetadataCheck()
      os_login_check.project_id = op.get(flags.PROJECT_ID)
      os_login_check.zone = op.get(flags.ZONE)
      os_login_check.instance_name = op.get(flags.INSTANCE_NAME)
      os_login_check.template = 'vm_metadata::no_os_login'
      os_login_check.metadata_key = 'enable_oslogin'
      os_login_check.expected_value = False
      self.add_child(os_login_check)
      self.add_child(PosixUserHasValidSshKeyCheck())
      self.add_child(VmDuplicateSshKeysCheck())


class PosixUserHasValidSshKeyCheck(runbook.Step):
  """Verifies the existence of a valid SSH key for the specified local Proxy user on a (VM).

  Ensures that the local user has at least one valid SSH key configured in the VM's metadata, which
  is essential for secure SSH access. The check is performed against the SSH keys stored within
  the VM's metadata. A successful verification indicates that the user is likely able to SSH into
  the VM using their key.
  """

  template = 'vm_metadata::valid_ssh_key'

  def execute(self):
    """Verify SSH key for local user."""

    vm = gce.get_instance(project_id=op.get(flags.PROJECT_ID),
                          zone=op.get(flags.ZONE),
                          instance_name=op.get(flags.INSTANCE_NAME))

    # Check if the local_user has a valid key in the VM's metadata.
    ssh_keys = vm.get_metadata('ssh-keys').split('\n') if vm.get_metadata(
        'ssh-keys') else []
    has_valid_key = util.user_has_valid_ssh_key(op.get(flags.POSIX_USER),
                                                ssh_keys)
    if has_valid_key:
      op.add_ok(resource=vm,
                reason=op.prep_msg(op.SUCCESS_REASON,
                                   local_user=op.get(flags.POSIX_USER),
                                   full_resource_path=vm.full_path))
    else:
      op.add_failed(vm,
                    reason=op.prep_msg(op.FAILURE_REASON,
                                       local_user=op.get(flags.POSIX_USER),
                                       full_resource_path=vm.full_path),
                    remediation=op.prep_msg(op.FAILURE_REMEDIATION,
                                            local_user=op.get(
                                                flags.POSIX_USER)))


class VmDuplicateSshKeysCheck(runbook.Step):
  """Check if there are duplicate ssh keys in VM metadata."""

  template = 'vm_metadata::duplicate_ssh_keys'

  def execute(self):
    """Check for duplicate SSH keys."""
    vm = gce.get_instance(
        project_id=op.get(flags.PROJECT_ID),
        zone=op.get(flags.ZONE),
        instance_name=op.get(flags.INSTANCE_NAME),
    )
    ssh_keys_str = vm.get_metadata('ssh-keys')
    if not ssh_keys_str:
      op.add_ok(vm, reason='No SSH keys found in metadata.')
      return

    key_blobs = []
    for line in ssh_keys_str.splitlines():
      line = line.strip()
      if not line:
        continue

      # remove username prefix if present
      line_parts = line.split(':', 1)
      if len(line_parts) == 2 and ' ' not in line_parts[0]:
        line_without_user = line_parts[1]
      else:
        line_without_user = line

      parts = line_without_user.strip().split()
      if len(parts) >= 2:
        # parts[0] is key type, parts[1] is key blob
        key_blobs.append(parts[1])

    seen = set()
    duplicates = []
    for blob in key_blobs:
      if blob in seen and blob not in duplicates:
        duplicates.append(blob)
      else:
        seen.add(blob)

    if duplicates:
      op.add_failed(
          vm,
          reason=op.prep_msg(op.FAILURE_REASON,
                             instance_name=vm.name,
                             count=len(duplicates),
                             keys=','.join(duplicates)),
          remediation=op.prep_msg(op.FAILURE_REMEDIATION),
      )
    else:
      op.add_ok(vm,
                reason=op.prep_msg(op.SUCCESS_REASON, instance_name=vm.name))


class GceFirewallAllowsSsh(runbook.Gateway):
  """Assesses the VPC network configuration to ensure it allows SSH traffic to the target VM.

  This diagnostic step checks for ingress firewall rules that permit SSH traffic based on
  the operational context, such as the use of IAP for SSH or direct access from a specified
  source IP. It helps identify network configurations that might block SSH connections."""

  def execute(self):
    """Evaluating VPC network firewall rules for SSH access."""
    vm = gce.get_instance(project_id=op.get(flags.PROJECT_ID),
                          zone=op.get(flags.ZONE),
                          instance_name=op.get(flags.INSTANCE_NAME))

    if op.get(flags.PROXY) == IAP:
      tti_ingress_check = gce_gs.GceVpcConnectivityCheck()
      tti_ingress_check.project_id = op.get(flags.PROJECT_ID)
      tti_ingress_check.zone = op.get(flags.ZONE)
      tti_ingress_check.instance_name = op.get(flags.INSTANCE_NAME)
      tti_ingress_check.src_ip = op.get(flags.SRC_IP)
      tti_ingress_check.protocol_type = 'tcp'
      tti_ingress_check.port = op.get(flags.PORT)
      tti_ingress_check.traffic = 'ingress'
      # Check IAP Firewall rule if specified
      tti_ingress_check.template = 'vpc_connectivity::tti_ingress'
      self.add_child(tti_ingress_check)
    if (not op.get(flags.SRC_IP) and not op.get(flags.PROXY) and
        vm.is_public_machine()):
      default_ingress_check = gce_gs.GceVpcConnectivityCheck()
      default_ingress_check.project_id = op.get(flags.PROJECT_ID)
      default_ingress_check.zone = op.get(flags.ZONE)
      default_ingress_check.instance_name = op.get(flags.INSTANCE_NAME)
      default_ingress_check.src_ip = op.get(flags.SRC_IP)
      default_ingress_check.protocol_type = 'tcp'
      default_ingress_check.port = op.get(flags.PORT)
      default_ingress_check.traffic = 'ingress'
      default_ingress_check.template = 'vpc_connectivity::default_ingress'

      self.add_child(default_ingress_check)

    # Check provided source IP has access
    if op.get(flags.SRC_IP) and not op.get(flags.PROXY):
      custom_ip_ingress_check = gce_gs.GceVpcConnectivityCheck()
      custom_ip_ingress_check.project_id = op.get(flags.PROJECT_ID)
      custom_ip_ingress_check.zone = op.get(flags.ZONE)
      custom_ip_ingress_check.instance_name = op.get(flags.INSTANCE_NAME)
      custom_ip_ingress_check.src_ip = op.get(flags.SRC_IP)
      custom_ip_ingress_check.protocol_type = 'tcp'
      custom_ip_ingress_check.port = op.get(flags.PORT)
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
    """Evaluating VM memory, CPU, and disk performance."""
    vm_memory_check = gce_gs.HighVmMemoryUtilization()
    vm_memory_check.project_id = op.get(flags.PROJECT_ID)
    vm_memory_check.zone = op.get(flags.ZONE)
    vm_memory_check.instance_name = op.get(flags.INSTANCE_NAME)
    vm_disk_check = gce_gs.HighVmDiskUtilization()
    vm_disk_check.project_id = op.get(flags.PROJECT_ID)
    vm_disk_check.zone = op.get(flags.ZONE)
    vm_disk_check.instance_name = op.get(flags.INSTANCE_NAME)
    vm_cpu_check = gce_gs.HighVmCpuUtilization()
    vm_cpu_check.project_id = op.get(flags.PROJECT_ID)
    vm_cpu_check.zone = op.get(flags.ZONE)
    vm_cpu_check.instance_name = op.get(flags.INSTANCE_NAME)
    self.add_child(child=vm_memory_check)
    self.add_child(child=vm_disk_check)
    self.add_child(child=vm_cpu_check)


class LinuxGuestOsChecks(runbook.CompositeStep):
  """Examines Linux-based guest OS's serial log entries for guest os level issues.

  This composite step scrutinizes the VM's serial logs for patterns indicative of kernel panics,
  problems with the SSH daemon, and blocks by SSH Guard - each of which could signify underlying
  issues affecting the VM's stability and accessibility. By identifying these specific patterns,
  the step aims to isolate common Linux OS and application issues, facilitating targeted
  troubleshooting.
  """

  def execute(self):
    """Analyzing serial logs for common linux guest os and application issues."""
    # Check for kernel panic patterns in serial logs.
    kernel_panic = gce_gs.VmSerialLogsCheck()
    kernel_panic.project_id = op.get(flags.PROJECT_ID)
    kernel_panic.zone = op.get(flags.ZONE)
    kernel_panic.instance_name = op.get(flags.INSTANCE_NAME)
    kernel_panic.template = 'vm_serial_log::kernel_panic'
    kernel_panic.negative_pattern = gce_const.KERNEL_PANIC_LOGS
    kernel_panic.positive_pattern = ['systemd', 'OSConfigAgent']

    self.add_child(kernel_panic)
    # Check for issues in SSHD configuration or behavior.
    sshd_check = gce_gs.VmSerialLogsCheck()
    sshd_check.project_id = op.get(flags.PROJECT_ID)
    sshd_check.zone = op.get(flags.ZONE)
    sshd_check.instance_name = op.get(flags.INSTANCE_NAME)
    sshd_check.template = 'vm_serial_log::sshd'
    sshd_check.negative_pattern = gce_const.BAD_SSHD_PATTERNS
    sshd_check.positive_pattern = gce_const.GOOD_SSHD_PATTERNS
    self.add_child(sshd_check)
    # Check for SSH Guard blocks that might be preventing SSH access.
    sshd_guard = gce_gs.VmSerialLogsCheck()
    sshd_guard.project_id = op.get(flags.PROJECT_ID)
    sshd_guard.zone = op.get(flags.ZONE)
    sshd_guard.instance_name = op.get(flags.INSTANCE_NAME)
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
    """Analyzing Windows Guest OS boot-up and SSH agent status."""
    # Check Windows Metadata enabling ssh is set as this is required for windows
    windows_ssh_md = gce_gs.VmMetadataCheck()
    windows_ssh_md.project_id = op.get(flags.PROJECT_ID)
    windows_ssh_md.zone = op.get(flags.ZONE)
    windows_ssh_md.instance_name = op.get(flags.INSTANCE_NAME)
    windows_ssh_md.template = 'vm_metadata::windows_ssh_md'
    windows_ssh_md.metadata_key = 'enable-windows-ssh'
    windows_ssh_md.expected_value = True
    self.add_child(windows_ssh_md)

    windows_good_bootup = gce_gs.VmSerialLogsCheck()
    windows_good_bootup.project_id = op.get(flags.PROJECT_ID)
    windows_good_bootup.zone = op.get(flags.ZONE)
    windows_good_bootup.instance_name = op.get(flags.INSTANCE_NAME)
    windows_good_bootup.template = 'vm_serial_log::windows_bootup'
    windows_good_bootup.positive_pattern = gce_const.GOOD_WINDOWS_BOOT_LOGS_READY
    self.add_child(windows_good_bootup)

    check_windows_ssh_agent = gcp_gs.HumanTask()
    check_windows_ssh_agent.project_id = op.get(flags.PROJECT_ID)
    check_windows_ssh_agent.zone = op.get(flags.ZONE)
    check_windows_ssh_agent.instance_name = op.get(flags.INSTANCE_NAME)
    check_windows_ssh_agent.template = (
        'gcpdiag.runbook.gce::vm_serial_log::windows_gce_ssh_agent')

    vm = gce.get_instance(project_id=op.get(flags.PROJECT_ID),
                          zone=op.get(flags.ZONE),
                          instance_name=op.get(flags.INSTANCE_NAME))
    check_windows_ssh_agent.resource = vm
    check_windows_ssh_agent.template = 'gcpdiag.runbook.gce::vm_serial_log::windows_gce_ssh_agent'
    self.add_child(check_windows_ssh_agent)
