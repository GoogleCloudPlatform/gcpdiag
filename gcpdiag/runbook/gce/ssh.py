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
from gcpdiag.runbook import PyDiagnosticTreeBuilder
from gcpdiag.runbook import common_steps as global_cs
from gcpdiag.runbook.gce import common_steps as gce_cs
from gcpdiag.runbook.gce import constants as gce_const
from gcpdiag.runbook.gce import util
# pylint: disable=unused-wildcard-import
# pylint: disable=wildcard-import
from gcpdiag.runbook.gce.parameters import *


class Ssh(runbook.DiagnosticTree):
  """Analyzes typical factors that might impede SSH connectivity

  Investigates the following for a single windows or linux VM:

  - VM Instance Status: Inspects the VM's lifecycle, CPU, memory, and disk status.
  - User Permissions: Verifies Google Cloud IAM permissions necessary for utilizing
    OS login and metadata-based SSH keys.
  - VM Configuration: Verifies the presence or absence of required metadata.
  - GCE Network connectivity tests: Inspects firewall rules to ensure user can reach the VM.
  - Internal GuestOS checks: Checks for signs of internal Guest OS issues.
  """
  req_params = {
      NAME_FLAG: 'Instance Name',
      ZONE_FLAG: 'Zone of the instance',
      PRINCIPAL_FLAG: 'User or service account email address'
  }

  def build_tree(self):
    builder = PyDiagnosticTreeBuilder(tree=self)
    start = SshStartStep()
    lifecycle_check = gce_cs.GCEInRunningState()
    performance_check = CheckVMPerformance()
    gce_permission_check = GCESshUserPermission()
    gce_firewall_check = GCEFirewallNetworkAllowsSsh()
    guestos_gateway = GuestOSType(paths={
        LINUX: LinuxGuestOsChecks(),
        WINDOWS: WindowsGuestOSChecks()
    })
    # Prepare parameters given by the user
    # Inform the user values that will be used.
    builder.add_start(step=start)
    # First check VM is running
    builder.add_step(parent=start, child=lifecycle_check)
    # Only check performance if VM is up and running.
    builder.add_step(parent=lifecycle_check, child=performance_check)
    # Check the state of the guest os after performance checks
    builder.add_step(parent=lifecycle_check, child=guestos_gateway)
    # gce_* checks are not depend on the lifecycle, performnce or guest of the VM
    # assign add as a child of start
    builder.add_step(parent=start, child=gce_permission_check)
    builder.add_step(parent=start, child=gce_firewall_check)
    builder.add_end(step=SshEndStep())
    # Build the tree
    return builder.build()


class SshStartStep(runbook.StartStep):
  """Prepare SSH start"""

  def execute(self):
    """Starting SSH diagnostics"""
    project = crm.get_project(self.op.get(PROJECT_ID))

    try:
      vm = gce.get_instance(project_id=self.op.get(PROJECT_ID),
                            zone=self.op.get(ZONE_FLAG),
                            instance_name=self.op.get(NAME_FLAG))
    except googleapiclient.errors.HttpError:
      self.interface.add_skipped(
          project,
          reason=('Instance {} does not exist in zone {} or project {}').format(
              self.op.get(NAME_FLAG), self.op.get(ZONE_FLAG),
              self.op.get(PROJECT_ID)))
    else:
      if vm:
        # check if user supplied an instance id or a name.
        if self.op[NAME_FLAG].isdigit():
          self.op[NAME_FLAG] = vm.name
        # Perform basic parameter checks and parse
        # string boolean into boolean values
        if gce_const.BOOL_VALUES[self.op.get(OS_LOGIN_FLAG)]:
          self.op[OS_LOGIN_FLAG] = True
          self.interface.info('Will check for OS login configuration')
        else:
          self.op[OS_LOGIN_FLAG] = False
          self.interface.info(
              'Will check for Metadata based SSH key configuration')
        if self.op.get(SRC_IP_FLAG):
          try:
            ip = ipaddress.ip_network(self.op.get(SRC_IP_FLAG))
          except ValueError:
            self.interface.add_skipped(
                project,
                reason=
                ('src_ip {} is not a valid IPv4/IPv6 address or CIDR range. Provide a'
                 ' Valid IPv4/IPv6 Address or CIDR range').format(
                     self.op.get(SRC_IP_FLAG)))
          else:
            self.op[SRC_IP_FLAG] = ip
            self.interface.info('Checks will use ip {} as the source IP'.format(
                self.op.get(SRC_IP_FLAG)))
        elif (not self.op.get(SRC_IP_FLAG) and not self.op.get(TTI_FLAG) and
              vm.is_public_machine()):
          self.op[SRC_IP_FLAG] = gce_const.UNSPECIFIED_ADDRESS
        if gce_const.BOOL_VALUES[self.op.get(TTI_FLAG)]:
          self.op[TTI_FLAG] = True
          # set IAP VIP as the source to the VM
          self.op[SRC_IP_FLAG] = gce_const.IAP_FW_VIP
          self.interface.info('Will check for IAP configuration')
        else:
          self.op[TTI_FLAG] = False
          self.interface.info(
              'Will not check for IAP for TCP forwarding configuration')
        if self.op.get(LOCAL_USER_FLAG):
          self.op[LOCAL_USER_FLAG] = self.op.get(LOCAL_USER_FLAG)
          self.interface.info(
              f'Local User: {self.op.get(LOCAL_USER_FLAG)} will be used '
              f'examine metadata-based SSH Key configuration')
        if self.op.get(PRINCIPAL_FLAG):
          email_only = len(self.op.get(PRINCIPAL_FLAG).split(':')) == 1
          if email_only:
            # Get the type
            p_policy = iam.get_project_policy(vm.project_id)
            p_type = p_policy.get_member_type(self.op.get(PRINCIPAL_FLAG))
            self.op[PRINCIPAL_FLAG] = f'{p_type}:{self.op.get(PRINCIPAL_FLAG)}'
            if p_type:
              self.interface.info(
                  f'Checks will use {self.op.get(PRINCIPAL_FLAG)} as the authenticated\n'
                  'principal in Cloud Console / gcloud (incl. impersonated service account)'
              )
            else:
              # groups and org principals are not expanded.
              # prompt until groups and inherited principals expanded
              # for projects.
              pass
        # Set IP protocol
        self.op[PROTOCOL_TYPE] = 'tcp'
        if not self.op.get(PORT_FLAG):
          self.op[PORT_FLAG] = gce_const.DEFAULT_SSHD_PORT

    ops_agent_q = monitoring.query(
        self.op.get(PROJECT_ID), """
              fetch gce_instance
              | metric 'agent.googleapis.com/agent/uptime'
              | filter (metadata.system_labels.name == '{}')
              | align rate(5m)
              | every 5m
              | {}
            """.format(self.op.get(NAME_FLAG), gce_cs.within_str))
    if ops_agent_q:
      self.interface.info('Will use ops agent metrics for relevant assessments')
      self.op[OPS_AGENT_INSTALLED] = True


LINUX = 'linux-distro'
WINDOWS = 'windows'


class GuestOSType(runbook.Gateway):
  """Checking Guest OS Type Used on VM"""

  def execute(self):
    """Checking Guest OS Type Used on VM"""
    vm = gce.get_instance(project_id=self.op.get(PROJECT_ID),
                          zone=self.op.get(ZONE_FLAG),
                          instance_name=self.op.get(NAME_FLAG))
    if not vm.is_windows_machine():
      self.interface.info(
          'Guest Os is a Linux VM. Investigating Linux related issues')
      self.add_step(self.paths[LINUX])
    else:
      self.interface.info(
          'Guest Os is a Windows VM. Investigating Windows related issues')
      self.add_step(self.paths[WINDOWS])


class SshEndStep(runbook.EndStep):
  """End step for SSH"""

  def execute(self):
    """End step for SSH"""
    if not config.get(AUTO):
      response = self.interface.prompt(
          step=self.interface.output.CONFIRMATION,
          message=f'Are you able to SSH into VM {self.op.get(NAME_FLAG)}?')
      if response == self.interface.output.NO:
        self.interface.info(message=(
            'Refer to our documentation on troubleshooting SSH\n'
            'https://cloud.google.com/compute/docs/trouble'
            'shooting/troubleshooting-ssh-errors\n\n'
            'Contact Google Cloud Support for further investigation.\n'
            'https://cloud.google.com/support/docs/customer-care-procedures\n'
            'Recommended: Submit the generated report to Google cloud support if opening a ticket.'
        ))


class GCESshUserPermission(runbook.CompositeStep):
  """Checking overall GCP permissions required for provided parameters"""

  def execute(self):
    """Checking overall GCP permissions required for provided parameters
    Note: Only roles granted at the project level are checked. Permissions inherited from
    ancestor resources such as folder(s) or organization and groups are not checked."""
    # Check user has permisssion to access the VM in the first place
    self.add_step(gce_cs.UserCanViewCloudConsole())
    # Both OS login and gcloud key based require this.
    self.add_step(UserHasPermissionToFetchVM())

    if not self.op.get(OS_LOGIN_FLAG):
      self.add_step(AuthUserHasComputeMetadataPermissions())
      os_login_check = gce_cs.GCEBooleanMetadataCheck()
      os_login_check.prompts[gce_const.FAILURE_REASON] = (
          'OS login is enabled on the VM, for a metadata-based SSH Key approach\n'
          'Note: Metadata-based SSH key authentication will not work on the VM.'
      )
      os_login_check.prompts[gce_const.FAILURE_REMEDIATION] = (
          'When you set OS Login metadata, Compute Engine deletes the VM\'s authorized_keys\n'
          'file and no longer accepts connections using SSH keys stored in project/instance\n'
          'metadata. You must choosing between OS login or metadata based SSH key approach.\n'
          'If you wish to use metadata ssh keys set the metadata `enable-oslogin=False`\n'
          'https://cloud.google.com/compute/docs/oslogin/set-up-oslogin#enable_os_login'
      )
      os_login_check.prompts[gce_const.SUCCESS_REASON] = (
          'User does not intend to use OS Login, and the `enable-oslogin`\n'
          'flag is not enabled on the VM.')
      os_login_check.METADATA_KEY = 'enable-oslogin'
      os_login_check.METADATA_VALUE = False
      os_login_check.prompts[
          gce_const.STEP_MESSAGE] = 'Checking OS Login Feature is enabled on VM'
      self.add_step(os_login_check)
      self.add_step(PoxisUserHasValidSSHKey())

    # User intends to use OS login
    if self.op.get(OS_LOGIN_FLAG):
      os_login_check = gce_cs.GCEBooleanMetadataCheck()
      os_login_check.prompts[
          gce_const.
          FAILURE_REASON] = 'The user intends to use OS login, but OS login is currently disabled.'
      os_login_check.prompts[gce_const.FAILURE_REMEDIATION] = (
          'To enable OS login, add the `enable-oslogin` flag to the VM\'s metadata.\n'
          'This is required for using OS login.\n'
          'https://cloud.google.com/compute/docs/oslogin/set-up-oslogin#enable_os_login'
      )
      os_login_check.prompts[gce_const.SUCCESS_REASON] = (
          'The VM has the `enable-oslogin` flag enabled, allowing OS login.')
      os_login_check.METADATA_KEY = 'enable-oslogin'
      os_login_check.METADATA_VALUE = True
      os_login_check.prompts[
          gce_const.STEP_MESSAGE] = 'Checking OS Login Feature is enabled on VM'
      self.add_step(os_login_check)
      self.add_step(AuthUserHasOSLoginPermissions())
      self.add_step(AuthUserHasServiceAccountUser())

    if self.op.get(TTI_FLAG):
      self.add_step(AuthUserHasIAPTunnelUserPermissions())


class AuthUserHasComputeMetadataPermissions(runbook.Step):
  """Checks required for update SSH metadata in Project or instance"""

  metadata_permissions = [
      'compute.instances.setMetadata',
      'compute.projects.setCommonInstanceMetadata'
  ]

  def execute(self):
    """Checking permissions required for update SSH metadata in a project or instance
    Note: Only roles granted at the project level are checked. Permissions inherited from
    ancestor resources such as folder(s) or organization and groups are not checked."""

    iam_policy = iam.get_project_policy(self.op.get(PROJECT_ID))

    auth_user = self.op.get(PRINCIPAL_FLAG)
    can_set_metadata = iam_policy.has_any_permission(auth_user,
                                                     self.metadata_permissions)
    if can_set_metadata:
      self.interface.add_ok(
          resource=iam_policy,
          reason=
          (f'{auth_user} has permission to set instance or project metadata (ssh keys)'
          ))
    else:
      self.interface.add_failed(
          iam_policy,
          reason=
          (f'The authenticated user lacks the necessary permissions for managing metadata.\n'
           f'Required permissions: {" or ".join(self.metadata_permissions)}.'),
          # TODO: find better resource talking about how metadata permission works
          remediation=
          ('To resolve this issue, ensure the user has the following metadata permissions:\n'
           ' - Add SSH Key to project-level metadata: https://cloud.google.com/'
           'compute/docs/connect/add-ssh-keys#expandable-2\n'
           ' - Add SSH Key to instance-level metadata: https://cloud.google.com/'
           'compute/docs/connect/add-ssh-keys#expandable-3'))


class UserHasPermissionToFetchVM(runbook.Step):
  """Checking permissions required to fetch an instance"""

  # Instance related permissions variables
  instance_permissions = ['compute.instances.get', 'compute.instances.use']

  def execute(self):
    """Checking permissions required to fetch an instance
    Note: Only roles granted at the project level are checked. Permissions inherited from
    ancestor resources such as folder(s) or organization and groups are not checked."""

    iam_policy = iam.get_project_policy(self.op.get(PROJECT_ID))

    auth_user = self.op.get(PRINCIPAL_FLAG)
    if iam_policy.has_any_permission(auth_user, self.instance_permissions):
      self.interface.add_ok(resource=iam_policy,
                            reason='User has permission to get instance')
    else:
      self.interface.add_failed(
          iam_policy,
          reason=
          ('The authenticated user lacks the required permissions for managing instances.\n'
           f'Required permissions: {", ".join(self.instance_permissions)}.'),
          remediation=
          (f'Grant principal {auth_user} a role with the following permissions:\n'
           f' - {", ".join(self.instance_permissions)}\n'
           'For instructions, refer to the documentation on connecting with instance admin roles:\n'
           'https://cloud.google.com/compute/docs/access/iam#connectinginstanceadmin'
          ))


class PoxisUserHasValidSSHKey(runbook.Step):
  """Checking if the Local User provided has a valid SSH key
    Note: Only roles granted at the project level are checked. Permissions inherited from
    ancestor resources such as folder(s) or organization and groups are not checked."""

  def execute(self):
    """Checking if the Local User provided has a valid SSH key
    Note: Only roles granted at the project level are checked. Permissions inherited from
    ancestor resources such as folder(s) or organization and groups are not checked."""

    vm = gce.get_instance(project_id=self.op.get(PROJECT_ID),
                          zone=self.op.get(ZONE_FLAG),
                          instance_name=self.op.get(NAME_FLAG))

    # check if the local_user has a valid key
    ssh_keys = vm.get_metadata('ssh-keys').split('\n') if vm.get_metadata(
        'ssh-keys') else []
    has_valid_key = util.user_has_valid_ssh_key(self.op.get(LOCAL_USER_FLAG),
                                                ssh_keys)
    if has_valid_key:
      self.interface.add_ok(
          resource=vm,
          reason=
          (f'Local user "{self.op.get(LOCAL_USER_FLAG)}" has at least one valid SSH\n'
           f'key VM: {vm.name}.'))
    else:
      self.interface.add_failed(
          vm,
          reason=(
              f'Local user "{self.op.get(LOCAL_USER_FLAG)}" does not have at '
              f'least one valid SSH key for the VM. {vm.name}'),
          remediation=
          ('To resolve this issue, add a valid SSH key for the user '
           f'"{self.op.get(LOCAL_USER_FLAG)}" by following the instructions:\n'
           'https://cloud.google.com/compute/docs/connect/add-ssh-keys#add_ssh_keys_to'
           '_instance_metadata\n'))


class AuthUserHasOSLoginPermissions(runbook.Step):
  """Checking permissions required to use OSlogin"""

  def execute(self):
    """Checking permissions required to use OSlogin
    Note: Only roles granted at the project level are checked. Permissions inherited from
    ancestor resources such as folder(s) or organization and groups are not checked."""

    vm = gce.get_instance(project_id=self.op.get(PROJECT_ID),
                          zone=self.op.get(ZONE_FLAG),
                          instance_name=self.op.get(NAME_FLAG))
    iam_policy = iam.get_project_policy(self.op.get(PROJECT_ID))

    auth_user = self.op.get(PRINCIPAL_FLAG)

    # Does the instance have a service account?
    # Then users needs to have permissions to user the service account
    if not (iam_policy.has_role_permissions(
        f'{auth_user}',
        gce_const.OSLOGIN_ROLE) or iam_policy.has_role_permissions(
            auth_user, gce_const.OSLOGIN_ADMIN_ROLE or
            iam_policy.has_role_permissions(auth_user, gce_const.OWNER_ROLE))):
      self.interface.add_failed(
          iam_policy,
          reason=(f'{auth_user} is missing at least of these required\n'
                  f'{gce_const.OSLOGIN_ROLE} or {gce_const.OSLOGIN_ADMIN_ROLE} '
                  f'or {gce_const.OSLOGIN_ADMIN_ROLE}'),
          remediation=(
              f'Grant {auth_user} of the following roles:'
              f'\n{gce_const.OSLOGIN_ROLE} or {gce_const.OSLOGIN_ADMIN_ROLE}'
              f'\nHelp Resources:\n'
              'https://cloud.google.com/compute/docs/oslogin/'
              'set-up-oslogin#configure_users\n'
              'https://cloud.google.com/iam/docs/manage-access'
              '-service-accounts#grant-single-role'))
    else:
      self.interface.add_ok(
          resource=vm,
          reason=(f'{auth_user} has at least one of the mandatory roles: \n'
                  f'{gce_const.OSLOGIN_ROLE} or {gce_const.OSLOGIN_ADMIN_ROLE} '
                  f' or {gce_const.OWNER_ROLE}'))


class AuthUserHasServiceAccountUser(runbook.Step):
  """Checking permissions required to use a VM with service account attached"""

  def execute(self):
    """Checking permissions required to use a VM with service account attached
    Note: Only roles granted at the project level are checked. Permissions inherited from
    ancestor resources such as folder(s) or organization and groups are not checked."""

    vm = gce.get_instance(project_id=self.op.get(PROJECT_ID),
                          zone=self.op.get(ZONE_FLAG),
                          instance_name=self.op.get(NAME_FLAG))
    iam_policy = iam.get_project_policy(vm.project_id)

    auth_user = self.op.get(PRINCIPAL_FLAG)

    if vm.service_account:
      if not iam_policy.has_role_permissions(auth_user, gce_const.SA_USER_ROLE):
        self.interface.add_failed(
            vm,
            reason=f'{auth_user} is missing'
            f'mandatory {gce_const.SA_USER_ROLE} on attached service account {vm.service_account}',
            remediation=(f'Grant {auth_user} {gce_const.SA_USER_ROLE}\n'
                         'Resources:\n'
                         'https://cloud.google.com/compute/docs/oslogin/'
                         'set-up-oslogin#configure_users\n'
                         'https://cloud.google.com/iam/docs/manage-access'
                         '-service-accounts#grant-single-role'))
      else:
        self.interface.add_ok(
            resource=vm,
            reason=(
                f'VM has a service account and principal {auth_user} has\n'
                f'required {gce_const.SA_USER_ROLE} on {vm.service_account}'))


class AuthUserHasIAPTunnelUserPermissions(runbook.Step):
  """Checking permissions required to tunnel via IAP to a VM"""

  def execute(self):
    """Checking permissions required to tunnel via IAP to a VM
    Note: Only roles granted at the project level are checked. Permissions inherited from
    ancestor resources such as folder(s) or organization and groups are not checked."""

    vm = gce.get_instance(project_id=self.op.get(PROJECT_ID),
                          zone=self.op.get(ZONE_FLAG),
                          instance_name=self.op.get(NAME_FLAG))
    iam_policy = iam.get_project_policy(self.op.get(PROJECT_ID))

    auth_user = self.op.get(PRINCIPAL_FLAG)
    # Check for IAP config
    # TODO improve this to check that it affects the
    #  interested instance. because IAP and Service account roles can be scoped to VM
    if not iam_policy.has_role_permissions(f'{auth_user}', gce_const.IAP_ROLE):
      self.interface.add_failed(
          iam_policy,
          reason=f'{auth_user} is missing mandatory\n{gce_const.IAP_ROLE}',
          remediation=(f'Grant {auth_user} {gce_const.IAP_ROLE}\n'
                       'Resources: '
                       'https://cloud.google.com/compute/docs/oslogin/'
                       'set-up-oslogin#configure_users\n'
                       'https://cloud.google.com/iam/docs/manage-access'
                       '-service-accounts#grant-single-role'))
    else:
      self.interface.add_ok(
          resource=vm,
          reason=(f'Principal {auth_user} has required {gce_const.IAP_ROLE}'))


class GCEFirewallNetworkAllowsSsh(runbook.CompositeStep):
  """Checking Overall VPC network Configuration"""

  def execute(self):
    """Checking Overall VPC network Configuration"""
    vm = gce.get_instance(project_id=self.op.get(PROJECT_ID),
                          zone=self.op.get(ZONE_FLAG),
                          instance_name=self.op.get(NAME_FLAG))

    if self.op.get(TTI_FLAG):
      ingress_check = gce_cs.IngressTrafficAllowedForGCEInstance()
      # Check IAP Firewall rule if specified
      ingress_check.prompts[gce_const.FAILURE_REMEDIATION] = (
          'Allow ingress traffic from the VIP range 35.235.240.0/20\n'
          'https://cloud.google.com/compute/docs/troubleshooting/'
          'troubleshooting-ssh-errors#diagnosis_methods_for_linux_and_windows_vms'
      )

      self.add_step(ingress_check)
    if (not self.op.get(SRC_IP_FLAG) and not self.op.get(TTI_FLAG) and
        vm.is_public_machine()):
      tti_ingress_check = gce_cs.IngressTrafficAllowedForGCEInstance()
      tti_ingress_check.prompts[gce_const.FAILURE_REMEDIATION] = (
          'Consider using our recommended methods for connecting Compute Engine virtual\n'
          'machine (VM) instance through its internal IP address:\n'
          'https://cloud.google.com/compute/docs/connect/ssh-internal-ip')
      self.add_step(ingress_check)

    # Check provided source IP has access
    if self.op.get(SRC_IP_FLAG):
      self.add_step(gce_cs.IngressTrafficAllowedForGCEInstance())

    # TODO: add egress checks


class CheckVMPerformance(runbook.CompositeStep):
  """Checking Overall VM Performance"""

  def execute(self):
    """Checking Memory, CPU and Disk performance"""
    self.add_step(gce_cs.GCEHighMemoryUtilization())
    self.add_step(gce_cs.GCEHighDiskUtilization())
    self.add_step(gce_cs.GCEHighCPUPerformance())


class LinuxGuestOsChecks(runbook.CompositeStep):
  """Checking Linux OS & application issues through logs present in Serial Logs"""

  def execute(self):
    """Checking Linux OS & application issues through logs present in Serial Logs"""

    grub_check = gce_cs.GCESerialLogsCheck()
    # Failed boot logs
    grub_check.BAD_PATTERN = gce_const.KERNEL_PANIC_LOGS
    grub_check.prompts[
        gce_const.STEP_MESSAGE] = 'Checking Linux Guest Kernel Status'
    grub_check.prompts[
        gce_const.FAILURE_REASON] = gce_const.KERNEL_PANIC_FAILURE_REASON
    grub_check.prompts[
        gce_const.
        FAILURE_REMEDIATION] = gce_const.KERNEL_PANIC_FAILURE_REMEDIATION
    grub_check.prompts[
        gce_const.SUCCESS_REASON] = gce_const.KERNEL_PANIC_SUCCESS_REASON
    grub_check.prompts[
        gce_const.UNCERTAIN_REASON] = gce_const.KERNEL_PANIC_UNCERTAIN_REASON
    grub_check.prompts[
        gce_const.
        UNCERTAIN_REASON] = gce_const.KERNEL_PANIC_UNCERTAIN_REMEDIATION
    self.add_step(grub_check)

    sshd_check = gce_cs.GCESerialLogsCheck()
    # Failed boot logs
    sshd_check.BAD_PATTERN = gce_const.BAD_SSHD_PATTERNS
    sshd_check.GOOD_PATTERN = gce_const.GOOD_SSHD_PATTERNS

    sshd_check.prompts[
        gce_const.STEP_MESSAGE] = 'Checking SSH Server Status via Serial Logs'
    sshd_check.prompts[gce_const.FAILURE_REASON] = gce_const.SSHD_FAILURE_REASON
    sshd_check.prompts[
        gce_const.FAILURE_REMEDIATION] = gce_const.SSHD_FAILURE_REMEDIATION
    sshd_check.prompts[gce_const.SUCCESS_REASON] = gce_const.SSHD_SUCCESS_REASON
    sshd_check.prompts[
        gce_const.UNCERTAIN_REASON] = gce_const.SSHD_UNCERTAIN_REASON
    sshd_check.prompts[
        gce_const.UNCERTAIN_REASON] = gce_const.SSHD_UNCERTAIN_REMEDIATION

    self.add_step(sshd_check)

    sshd_guard = gce_cs.GCESerialLogsCheck()
    # Failed boot logs
    sshd_guard.prompts[
        gce_const.
        STEP_MESSAGE] = 'Checking Intrusion Detection Software: SSH Guard'
    sshd_guard.prompts[
        gce_const.FAILURE_REASON] = gce_const.SSHGUARD_FAILURE_REASON
    sshd_guard.prompts[
        gce_const.FAILURE_REMEDIATION] = gce_const.SSHGUARD_FAILURE_REMEDIATION
    sshd_guard.prompts[
        gce_const.SUCCESS_REASON] = gce_const.SSHGUARD_SUCCESS_REASON
    sshd_guard.prompts[
        gce_const.UNCERTAIN_REASON] = gce_const.SSHGUARD_UNCERTAIN_REASON
    sshd_guard.prompts[
        gce_const.UNCERTAIN_REASON] = gce_const.SSHGUARD_UNCERTAIN_REMEDIATION

    sshd_guard.BAD_PATTERN = gce_const.SSHGUARD_PATTERNS
    self.add_step(sshd_guard)


class WindowsGuestOSChecks(runbook.CompositeStep):
  """Checks issues related to windows Guest OS"""

  # Typical logs of a fully booted windows VM
  GOOD_WINDOWS_BOOT_LOGS_READY = [
      'BdsDxe: starting',
      'UEFI: Attempting to start image',
      'Description: Windows Boot Manager',
      'GCEGuestAgent: GCE Agent Started',
      'OSConfigAgent Info: OSConfig Agent',
      'GCEMetadataScripts: Starting startup scripts',
  ]

  def execute(self):
    """Checking issues related windows Guest OS boot up and ssh agents"""
    # Check Windows Metadata enabling ssh is set as this is required for windows
    windows_ssh_md = gce_cs.GCEBooleanMetadataCheck()
    windows_ssh_md.prompts[
        gce_const.FAILURE_REASON] = gce_const.WINDOWS_SSH_MD_FAILURE_REASON
    windows_ssh_md.prompts[
        gce_const.
        FAILURE_REMEDIATION] = gce_const.WINDOWS_SSH_MD_FAILURE_REMEDIATION
    windows_ssh_md.prompts[
        gce_const.SUCCESS_REASON] = gce_const.WINDOWS_SSH_MD_SUCCESS_REASON
    windows_ssh_md.METADATA_KEY = 'enable-windows-ssh'
    windows_ssh_md.METADATA_VALUE = True
    self.add_step(windows_ssh_md)

    windows_good_bootup = gce_cs.GCESerialLogsCheck()
    # Failed boot logs
    windows_good_bootup.prompts[
        gce_const.STEP_MESSAGE] = 'Checking Windows OS has booted status'
    windows_good_bootup.prompts[
        gce_const.FAILURE_REASON] = gce_const.WINDOWS_BOOTUP_FAILURE_REASON
    windows_good_bootup.prompts[
        gce_const.
        FAILURE_REMEDIATION] = gce_const.WINDOWS_BOOTUP_FAILURE_REMEDIATION
    windows_good_bootup.prompts[
        gce_const.SUCCESS_REASON] = gce_const.WINDOWS_BOOTUP_SUCCESS_REASON
    windows_good_bootup.prompts[
        gce_const.UNCERTAIN_REASON] = gce_const.WINDOWS_BOOTUP_UNCERTAIN_REASON
    windows_good_bootup.prompts[
        gce_const.
        UNCERTAIN_REASON] = gce_const.WINDOWS_BOOTUP_UNCERTAIN_REMEDIATION

    windows_good_bootup.GOOD_PATTERN = self.GOOD_WINDOWS_BOOT_LOGS_READY
    self.add_step(windows_good_bootup)

    check_windows_ssh_agent = global_cs.HumanTask()
    vm = gce.get_instance(project_id=self.op.get(PROJECT_ID),
                          zone=self.op.get(ZONE_FLAG),
                          instance_name=self.op.get(NAME_FLAG))
    check_windows_ssh_agent.resource = vm
    check_windows_ssh_agent.prompts[
        gce_const.
        STEP_MESSAGE] = '''Manually check ssh reqired Agents are running on the VM
      Check google-compute-engine-ssh is installed.'''
    check_windows_ssh_agent.prompts[
        gce_const.
        INSTRUCTIONS_MESSAGE] = 'Is SSHD agent `google-compute-engine-ssh` installed on the VM'
    check_windows_ssh_agent.prompts[gce_const.INSTRUCTIONS_CHOICE_OPTIONS] = {
        'y': 'Yes',
        'n': 'No',
        'u': 'Unsure'
    }
    check_windows_ssh_agent.prompts[
        gce_const.
        FAILURE_REASON] = gce_const.WINDOWS_GCE_SSH_AGENT_FAILURE_REASON
    check_windows_ssh_agent.prompts[
        gce_const.
        FAILURE_REMEDIATION] = gce_const.WINDOWS_GCE_SSH_AGENT_FAILURE_REMEDIATION
    check_windows_ssh_agent.prompts[
        gce_const.
        SUCCESS_REASON] = gce_const.WINDOWS_GCE_SSH_AGENT_SUCCESS_REASON
    check_windows_ssh_agent.prompts[
        gce_const.
        UNCERTAIN_REASON] = gce_const.WINDOWS_GCE_SSH_AGENT_UNCERTAIN_REASON
    check_windows_ssh_agent.prompts[
        gce_const.
        UNCERTAIN_REASON] = gce_const.WINDOWS_GCE_SSH_AGENT_UNCERTAIN_REMEDIATION
    self.add_step(check_windows_ssh_agent)
