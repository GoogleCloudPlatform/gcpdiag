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
"""Analyzes typical factors that might impede SSH connectivity

Investigates the following for a single windows or linux VM:

- VM Instance Status: Inspects the VM's lifecycle, CPU, memory, and disk status.
- User Permissions: Verifies Google Cloud IAM permissions necessary for utilizing
  OS login and metadata-based SSH keys.
- VM Configuration: Verifies the presence or absence of required metadata.
- Network connectivity tests: Inspects firewall rules to ensure user can reach the VM.
"""

import ipaddress

import googleapiclient.errors

from gcpdiag import config, models, runbook
from gcpdiag.queries import crm, gce, iam, monitoring
from gcpdiag.runbook.gce import util

# unique flags belong to this runbook
TTI_FLAG = 'tunnel_through_iap'
NAME_FLAG = 'name'
ZONE_FLAG = 'zone'
PRINCIPAL_FLAG = 'principal'
SRC_IP_FLAG = 'src_ip'
OS_LOGIN_FLAG = 'os_login'
LOCAL_USER_FLAG = 'local_user'

# Runbook Flags
# Move this into superclass when using classes
AUTO = 'auto'

REQUIRED_PARAMETERS = {
    NAME_FLAG: 'Instance Name',
    ZONE_FLAG: 'Zone of the instance',
    PRINCIPAL_FLAG: 'User or service account email address'
}

OWNER_ROLE = 'roles/owner'
# Os login Permissions
OSLOGIN_ROLE = 'roles/compute.osLogin'
OSLOGIN_ADMIN_ROLE = 'roles/compute.osAdminLogin'
# Users from a different organization than the VM they're connecting to
OSLOGIN_EXTERNAL_USER_ROLE = 'roles/compute.osLoginExternalUser'
# All users, if the VM has a service account
SA_USER_ROLE = 'roles/iam.serviceAccountUser'
# TCP IAP
IAP_ROLE = 'roles/iap.tunnelResourceAccessor'
# INSTANCE ADMIN
INSTANCE_ADMIN_ROLE = 'roles/compute.instanceAdmin.v1'
# Typical logs of a fully booted windows VM
WINDOWS_ONLINE_READY = [
    'BdsDxe: starting',
    'UEFI: Attempting to start image',
    'Description: Windows Boot Manager',
    'GCEGuestAgent: GCE Agent Started',
    'OSConfigAgent Info: OSConfig Agent',
    'GCEMetadataScripts: Starting startup scripts',
]
# SSHD blocking logs
SSHGUARD_PATTERNS = [r'sshguard\[\d+\]: Blocking (\d+\.\d+\.\d+\.\d+)']

IAP_FW_VIP = ipaddress.ip_network('35.235.240.0/20')
SSHD_PORT = 22
DEFAULT_FW_RULE = ipaddress.ip_network('0.0.0.0/0')
NEXT_HOP = 'default-internet-gateway'

vm = None
project = None
ops_agent_installed = False
within_hours = 9
within_str = 'within %dh, d\'%s\'' % (within_hours,
                                      monitoring.period_aligned_now(5))


def start(context: models.Context,
          interface: runbook.RunbookInteractionInterface):
  """Starting SSH diagnostics"""
  global project
  project = crm.get_project(context.project_id)

  def task():
    global vm
    response = None
    try:
      vm = gce.get_instance(project_id=context.project_id,
                            zone=context.parameters[ZONE_FLAG],
                            instance_name=context.parameters[NAME_FLAG])
    except googleapiclient.errors.HttpError:
      response = interface.add_failed(
          project,
          reason=('Instance {} does not exist in zone {} or project {}').format(
              context.parameters.get(NAME_FLAG),
              context.parameters.get(ZONE_FLAG), context.project_id),
          remediation=(
              'Provide a valid instance in project {} and zone {}\n'
              'https://cloud.google.com/compute/docs/instances/get-list'
          ).format(context.project_id, context.parameters.get(ZONE_FLAG)))
      if (response is interface.CONTINUE or config.get(AUTO)):
        # fail hard if user does not fix this step or on runbook is autonomous
        return interface.ABORT
    else:
      if vm:
        # check if user supplied an instance id or a name.
        context.parameters[NAME_FLAG] = context.parameters[NAME_FLAG].strip()
        if context.parameters[NAME_FLAG].isdigit():
          context.parameters[NAME_FLAG] = vm.name
        # Perform basic parameter checks and parse
        # string boolean into boolean values
        if context.parameters.get(OS_LOGIN_FLAG,
                                  'false').strip().lower() == 'true':
          context.parameters[OS_LOGIN_FLAG] = True
          interface.prompt('Will check for OS login configuration')
        else:
          context.parameters[OS_LOGIN_FLAG] = False
          interface.prompt(
              'Will check for Metadata based SSH key configuration')
        if context.parameters.get(TTI_FLAG, 'false').strip().lower() == 'true':
          context.parameters[TTI_FLAG] = True
          interface.prompt('Will check for IAP configuration')
        else:
          context.parameters[TTI_FLAG] = False
          interface.prompt(
              'Will not check for IAP for TCP forwarding configuration')
        if context.parameters.get(SRC_IP_FLAG):
          try:
            ip = ipaddress.ip_network(
                context.parameters.get(SRC_IP_FLAG).strip())
          except ValueError:
            response = interface.add_failed(
                project,
                reason='src_ip {} is not a valid IPv4/IPv6 address or CIDR range'
                .format(context.parameters.get(SRC_IP_FLAG)),
                remediation='Provide a Valid IPv4/IPv6 Address or CIDR range')
            if (response is interface.CONTINUE or config.get(AUTO)):
              # fail hard if user does not fix this step or on runbook is autonomous
              return interface.ABORT
            context.parameters[SRC_IP_FLAG] = response
          else:
            context.parameters[SRC_IP_FLAG] = ip
            interface.prompt('Checks will use ip {} as the source IP'.format(
                context.parameters.get(SRC_IP_FLAG)))
        if context.parameters.get(LOCAL_USER_FLAG):
          context.parameters[LOCAL_USER_FLAG] = context.parameters.get(
              LOCAL_USER_FLAG).strip()
          interface.prompt(
              f'Local User: {context.parameters.get(LOCAL_USER_FLAG)} will be used '
              f'examine metadata-based SSH Key configuration')
        if context.parameters.get(PRINCIPAL_FLAG):
          context.parameters[PRINCIPAL_FLAG] = context.parameters.get(
              PRINCIPAL_FLAG).strip()
          email_only = len(
              context.parameters.get(PRINCIPAL_FLAG).split(':')) == 1
          if email_only:
            # Get the type
            p_policy = iam.get_project_policy(vm.project_id)
            p_type = p_policy.get_member_type(
                context.parameters.get(PRINCIPAL_FLAG))
            context.parameters[
                PRINCIPAL_FLAG] = f'{p_type}:{context.parameters.get(PRINCIPAL_FLAG)}'
            if p_type:
              interface.prompt(
                  f'Checks will use {context.parameters.get(PRINCIPAL_FLAG)} as the authenticated\n'
                  'principal in Cloud Console / gcloud (incl. impersonated service account)'
              )
            else:
              # groups and org principals are not expanded.
              # prompt until groups and inherited principals expanded
              # for projects.
              pass
    return response

  interface.execute_task(task)
  ops_agent_q = monitoring.query(
      context.project_id, """
            fetch gce_instance
            | metric 'agent.googleapis.com/agent/uptime'
            | filter (metadata.system_labels.name == '{}')
            | align rate(5m)
            | every 5m
            | {}
          """.format(context.parameters.get(NAME_FLAG), within_str))
  if ops_agent_q:
    global ops_agent_installed
    interface.prompt('Will use ops agent metrics for relevant assessments')
    ops_agent_installed = True
  return check_vm_lifecycle


def check_vm_lifecycle(context: models.Context,
                       interface: runbook.RunbookInteractionInterface):
  """Checking VM lifecycle state"""

  def task():
    global vm
    response = None
    vm = gce.get_instance(project_id=context.project_id,
                          zone=context.parameters.get(ZONE_FLAG),
                          instance_name=context.parameters.get(NAME_FLAG))
    if vm and vm.is_running():
      interface.add_ok(vm, reason=f'VM: {vm.name} is in a {vm.status} state.')
    else:
      # Register evaluation. Later used in generating a report for support.
      response = interface.add_failed(
          vm,
          reason=f'VM {vm.name} is in {vm.status} state.',
          remediation=
          ('To initiate the lifecycle transition of Virtual Machine (VM) {} '
           'to the RUNNING state:\n\n'
           'Start the VM:\n'
           'https://cloud.google.com/compute/docs/instances/stop-start-instance\n'
           'If you encounter any difficulties during the startup process, consult\n'
           'the troubleshooting documentation to identify and resolve potential startup issues:\n'
           'https://cloud.google.com/compute/docs/troubleshooting/'
           'vm-startup#identify_the_reason_why_the_boot_disk_isnt_booting'
          ).format(vm.name))
    return response

  interface.execute_task(task)
  return check_vm_performance


UTILIZATION_THRESHOLD = 0.95
# Failed boot logs
BOOT_ERROR_PATTERNS = [
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
# Typcial Memory exhaustion logs in serial console.
VM_OOM_PATTERN = [
    'Out of memory: Kill process', 'Kill process', 'Memory cgroup out of memory'
]
VM_DISK_SPACE_ERROR_PATTERN = [
    'No space left on device',
    'No usable temporary directory found in'
    # windows
    'disk is at or near capacity'
]


def check_vm_performance(context: models.Context,
                         interface: runbook.RunbookInteractionInterface):
  """Checking VM performance"""

  def task():
    response = None
    disk_usage = None
    cpu_usage = None
    mem_usage = None

    if ops_agent_installed:
      cpu_usage = monitoring.query(
          context.project_id, """
          fetch gce_instance
            | metric 'agent.googleapis.com/cpu/utilization'
            | filter (resource.instance_id == '{}')
            | group_by [resource.instance_id], 3m, [value_utilization_mean: mean(value.utilization)]
            | filter (cast_units(value_utilization_mean,"")/100) >= {}
            | {}
          """.format(vm.id, UTILIZATION_THRESHOLD, within_str))
      mem_usage = monitoring.query(
          context.project_id, """
          fetch gce_instance
            | metric 'agent.googleapis.com/memory/percent_used'
            | filter (resource.instance_id == '{}')
            | group_by [resource.instance_id], 3m, [percent_used: mean(value.percent_used)]
            | filter (cast_units(percent_used,"")/100) >= {}
            | {}
          """.format(vm.id, UTILIZATION_THRESHOLD, within_str))
      disk_usage = monitoring.query(
          context.project_id, """
        fetch gce_instance
            | metric 'agent.googleapis.com/disk/percent_used'
            | filter (resource.instance_id == '{}')
            | group_by [resource.instance_id], 3m, [percent_used: mean(value.percent_used)]
            | filter (cast_units(percent_used,"")/100) >= {}
            | {}
          """.format(vm.id, UTILIZATION_THRESHOLD, within_str))
    else:
      # use CPU utilization visible to the hypervisor
      cpu_usage = monitoring.query(
          context.project_id, """
            fetch gce_instance
              | metric 'compute.googleapis.com/instance/cpu/utilization'
              | filter (resource.instance_id == '{}')
              | group_by [resource.instance_id], 3m, [value_utilization_max: max(value.utilization)]
              | filter value_utilization_max >= {}
              | {}
            """.format(vm.id, UTILIZATION_THRESHOLD, within_str))
      if 'e2' in vm.machine_type():
        mem_usage = monitoring.query(
            context.project_id, """
              fetch gce_instance
                | {{ metric 'compute.googleapis.com/instance/memory/balloon/ram_used'
                ; metric 'compute.googleapis.com/instance/memory/balloon/ram_size' }}
                | outer_join 0
                | div
                | filter (resource.instance_id == '{}')
                | group_by [resource.instance_id], 3m, [ram_left: mean(val())]
                | filter ram_left >= {}
                | {}
              """.format(vm.id, UTILIZATION_THRESHOLD, within_str))
      # fallback on serial logs to see if there are OOM logs
      instance_serial_log = gce.get_instance_serial_port_output(
          project_id=context.project_id,
          zone=context.parameters.get(ZONE_FLAG),
          instance_name=context.parameters.get(NAME_FLAG))

      if 'e2' not in vm.machine_type():
        if instance_serial_log:
          mem_usage = util.search_pattern_in_serial_logs(
              VM_OOM_PATTERN, instance_serial_log.contents)

      if instance_serial_log:
        # All VM types + e2
        disk_usage = util.search_pattern_in_serial_logs(
            VM_DISK_SPACE_ERROR_PATTERN, instance_serial_log.contents)
    # Get Performance issues corrected.
    if cpu_usage:
      response = interface.add_failed(
          vm,
          reason=
          'CPU utilization is exceeding optimal levels, potentially impacting connectivity.',
          remediation=
          ('The VM is experiencing high CPU utilization, potentially causing sluggish connection\n'
           'Consider upgrading the CPU specifications for the VM instance and then restart it.\n'
           'For guidance on stopping a VM, refer to the documentation:\n'
           'https://cloud.google.com/compute/docs/instances/stop-start-instance.\n'
           'For more in-depth investigation, connect via the Serial Console to identify\n'
           'the problematic process:\n'
           'https://cloud.google.com/compute/docs/troubleshooting/'
           'troubleshooting-using-serial-console.'))

    else:
      interface.add_ok(
          vm,
          reason=('The VM is operating within optimal CPU utilization levels.'))

    if mem_usage:
      response = interface.add_failed(
          vm,
          reason=
          'Memory utilization is exceeding optimal levels, potentially impacting connectivity.',
          remediation=
          ('VM is experiencing high Memory utilization, potentially causing sluggish connections.\n'
           'Consider upgrading the Memory count for the VM instance and then restart it.\n'
           'Stopping and upgrading machine spec of a VM, refer to the documentation:\n'
           'https://cloud.google.com/compute/docs/instances/stop-start-instance.\n'
           'https://cloud.google.com/compute/docs/instances/changing-machine-type-'
           'of-stopped-instance#gcloud\n'
           'For more in-depth investigation, conntect via the Serial Console to resolve\n'
           'the problematic process:\n'
           'https://cloud.google.com/compute/docs/troubleshooting/'
           'troubleshooting-using-serial-console.'))
    else:
      interface.add_ok(
          vm,
          reason=(
              'The VM is operating within optimal memory utilization levels.'))

    if disk_usage:
      response = interface.add_failed(
          vm,
          reason=
          'Disk space utilization is exceeding optimal levels, potentially impacting connectivity.',
          remediation=
          ('The VM is experiencing high disk space utilization in the boot disk,\n'
           'potentially causing sluggish SSH connections.\n'
           'To address this, consider increasing the boot disk size of the VM:\n'
           'https://cloud.google.com/compute/docs/disks/resize-persistent-disk'
           '#increase_the_size_of_a_disk'))
    else:
      interface.add_ok(
          vm,
          ('The VM is operating within optimal disk space utilization levels.'))
    return response

  interface.execute_task(task)
  return check_user_permissions


# Instance related permissions variables
console_user_permission = 'compute.projects.get'
instance_permissions = ['compute.instances.get', 'compute.instances.use']
metadata_permissions = [
    'compute.instances.setMetadata',
    'compute.projects.setCommonInstanceMetadata'
]


def check_user_permissions(context: models.Context,
                           interface: runbook.RunbookInteractionInterface):
  """Checking permissions required for SSH
  Note: Only roles granted at the project level are checked. Permissions inherited from
  ancestor resources such as folder(s) or organization and groups are not checked."""

  def task():
    response = None
    can_set_metadata = False
    global vm
    vm = gce.get_instance(project_id=context.project_id,
                          zone=context.parameters.get(ZONE_FLAG),
                          instance_name=context.parameters.get(NAME_FLAG))
    iam_policy = iam.get_project_policy(vm.project_id)

    auth_user = context.parameters.get(PRINCIPAL_FLAG)
    # Check user has permisssion to access the VM in the first place
    if iam_policy.has_permission(auth_user, console_user_permission):
      interface.add_ok(
          resource=iam_policy,
          reason='User has permission to View the Console and compute resources'
      )
    else:
      response = interface.add_failed(
          iam_policy,
          f'To use the Google Cloud console to access Compute Engine, e.g. SSH in browser,\n'
          f'principal must have the {console_user_permission} permission.',
          'Refer to the documentation:\n'
          'https://cloud.google.com/compute/docs/access/iam#console_permission')

    if not context.parameters.get(OS_LOGIN_FLAG):
      # for key based approach auth user needs to be able to set metadata
      # Todo check later if instance metadata applies to the focus VM
      can_set_metadata = iam_policy.has_any_permission(auth_user,
                                                       metadata_permissions)
      if can_set_metadata:
        interface.add_ok(
            resource=iam_policy,
            reason=
            'User has permission to set instance or project metadata (ssh keys)'
        )
      else:
        response = interface.add_failed(
            iam_policy,
            reason=
            (f'The authenticated user lacks the necessary permissions for managing metadata.\n'
             f'Required permissions: {" or ".join(metadata_permissions)}.'),
            # TODO: find better resource talking about how metadata permission works
            remediation=
            ('To resolve this issue, ensure the user has the following metadata permissions:\n'
             ' - Add SSH Key to project-level metadata: https://cloud.google.com/'
             'compute/docs/connect/add-ssh-keys#expandable-2\n'
             ' - Add SSH Key to instance-level metadata: https://cloud.google.com/'
             'compute/docs/connect/add-ssh-keys#expandable-3'))
    # Both OS login and gcloud key based require this.
    if iam_policy.has_any_permission(auth_user, instance_permissions):
      interface.add_ok(resource=iam_policy,
                       reason='User has permission to get instance')
    else:
      response = interface.add_failed(
          iam_policy,
          reason=
          ('The authenticated user lacks the required permissions for managing instances.\n'
           f'Required permissions: {", ".join(instance_permissions)}.'),
          remediation=
          (f'Grant principal {auth_user} a role with the following permissions:\n'
           f' - {", ".join(instance_permissions)}\n'
           'For instructions, refer to the documentation on connecting with instance admin roles:\n'
           'https://cloud.google.com/compute/docs/access/iam#connectinginstanceadmin'
          ))

    if not context.parameters.get(OS_LOGIN_FLAG):
      if not vm.is_oslogin_enabled():
        # Oslogin should not be enabled or user is checking for metadata based user
        # on the VM and  oslogin feature is disabled.
        interface.add_ok(
            resource=vm,
            reason=
            ('User does not intend to use OS Login, and the `enable-oslogin`\n'
             'flag is not enabled on the VM.'))
      else:
        response = interface.add_failed(
            vm,
            reason=
            ('OS login is enabled on the VM, for a metadata-based SSH Key approach\n'
             'Note: Metadata-based SSH key authentication will not work on the VM.'
            ),
            remediation=
            ('When you set OS Login metadata, Compute Engine deletes the VM\'s authorized_keys\n'
             'file and no longer accepts connections using SSH keys stored in project/instance\n'
             'metadata. You must choosing between OS login or metadata based SSH key approach.\n'
             'If you wish to use metadata ssh keys set the metadata `enable-oslogin=False`\n'
             'https://cloud.google.com/compute/docs/oslogin/set-up-oslogin#enable_os_login'
            ))

      # check if the local_user has a valid key
      ssh_keys = vm.get_metadata('ssh-keys').split('\n') if vm.get_metadata(
          'ssh-keys') else []
      has_valid_key = util.user_has_valid_ssh_key(
          context.parameters.get(LOCAL_USER_FLAG), ssh_keys)
      if has_valid_key:
        interface.add_ok(
            resource=vm,
            reason=
            (f'Local user "{context.parameters.get(LOCAL_USER_FLAG)}" has at least one valid SSH\n'
             f'key VM: {vm.name}.'))
      else:
        response = interface.add_failed(
            vm,
            reason=
            (f'Local user "{context.parameters.get(LOCAL_USER_FLAG)}" does not have at '
             f'least one valid SSH key for the VM. {vm.name}'),
            remediation=
            ('To resolve this issue, add a valid SSH key for the user '
             f'"{context.parameters.get(LOCAL_USER_FLAG)}" by following the instructions:\n'
             'https://cloud.google.com/compute/docs/connect/add-ssh-keys#add_ssh_keys_to'
             '_instance_metadata\n'))

    if context.parameters.get(OS_LOGIN_FLAG):
      # Oslogin should be enabled on the VM if user wants to use oslogin
      # TODO: add checks for 2fa later.
      if vm.is_oslogin_enabled():
        interface.add_ok(
            resource=vm,
            reason=
            'The VM has the `enable-oslogin` flag enabled, allowing OS login.')
      else:
        response = interface.add_failed(
            vm,
            reason=
            'The user intends to use OS login, but OS login is currently disabled.',
            remediation=
            ('To enable OS login, add the `enable-oslogin` flag to the VM\'s metadata.\n'
             'This is required for using OS login.\n'
             'https://cloud.google.com/compute/docs/oslogin/set-up-oslogin#enable_os_login'
            ))
      # Does the instance have a service account?
      # Then users needs to have permissions to user the service account
      if not (iam_policy.has_role_permissions(f'{auth_user}', OSLOGIN_ROLE) or
              iam_policy.has_role_permissions(
                  f'{auth_user}', OSLOGIN_ADMIN_ROLE or
                  iam_policy.has_role_permissions(f'{auth_user}', OWNER_ROLE))):
        response = interface.add_failed(
            iam_policy,
            reason=(
                f'{auth_user} is missing at least of these required\n'
                f'{OSLOGIN_ROLE} or {OSLOGIN_ADMIN_ROLE} or {OSLOGIN_ADMIN_ROLE}'
            ),
            remediation=
            (f'Grant {auth_user} of the following roles:\n{OSLOGIN_ROLE} or {OSLOGIN_ADMIN_ROLE}'
             f'\nHelp Resources:\n'
             'https://cloud.google.com/compute/docs/oslogin/'
             'set-up-oslogin#configure_users\n'
             'https://cloud.google.com/iam/docs/manage-access'
             '-service-accounts#grant-single-role'))
      else:
        interface.add_ok(
            resource=vm,
            reason=(f'{auth_user} has at least one of the mandatory roles: \n'
                    f'{OSLOGIN_ROLE} or {OSLOGIN_ADMIN_ROLE} or {OWNER_ROLE}'))

      if vm.service_account:
        if not iam_policy.has_role_permissions(auth_user, SA_USER_ROLE):
          response = interface.add_failed(
              vm,
              reason=f'{auth_user} is missing'
              f'mandatory {SA_USER_ROLE} on attached service account {vm.service_account}',
              remediation=(f'Grant {auth_user} {SA_USER_ROLE}\n'
                           'Resources:\n'
                           'https://cloud.google.com/compute/docs/oslogin/'
                           'set-up-oslogin#configure_users\n'
                           'https://cloud.google.com/iam/docs/manage-access'
                           '-service-accounts#grant-single-role'))
        else:
          interface.add_ok(
              resource=vm,
              reason=(
                  f'VM has a service account and principal {auth_user} has\n'
                  f'required {SA_USER_ROLE} on {vm.service_account}'))

    if context.parameters.get(TTI_FLAG):
      # Check for IAP config
      # TODO improve this to check that it affects the
      #  interested instance. because IAP and Service account roles can be scoped to VM
      if not iam_policy.has_role_permissions(f'{auth_user}', IAP_ROLE):
        response = interface.add_failed(
            iam_policy,
            reason=f'{auth_user} is missing mandatory\n{IAP_ROLE}',
            remediation=(f'Grant {auth_user} {IAP_ROLE}\n'
                         'Resources: '
                         'https://cloud.google.com/compute/docs/oslogin/'
                         'set-up-oslogin#configure_users\n'
                         'https://cloud.google.com/iam/docs/manage-access'
                         '-service-accounts#grant-single-role'))
      else:
        interface.add_ok(
            resource=vm,
            reason=(f'Principal {auth_user} has required {IAP_ROLE}'))
        # Make sure they have access to to use the service account.
    return response

  interface.execute_task(task)
  return check_firewall_network_allows_ssh


def check_firewall_network_allows_ssh(
    context: models.Context, interface: runbook.RunbookInteractionInterface):
  """Checking VPC network"""

  def task():
    response = None
    result = None
    # Check provided source IP has access
    if context.parameters.get(SRC_IP_FLAG):
      result = vm.network.firewall.check_connectivity_ingress(
          src_ip=context.parameters.get(SRC_IP_FLAG),
          ip_protocol='tcp',
          port=SSHD_PORT,
          target_service_account=vm.service_account,
          target_tags=vm.tags)
      if result.action == 'deny':
        # Implied deny is a pass for IAP IP instances
        response = interface.add_failed(
            vm,
            reason=
            (f'Access from your Source IP "{context.parameters.get(SRC_IP_FLAG)} is not '
             f'allowed {result.matched_by_str or " "}'),
            remediation=
            ('If connecting to a non-public VM and do not wish to allow \n'
             'external access, choose one of the following connection options for VMs\n'
             'https://cloud.google.com/compute/docs/connect/ssh-internal-ip\n\n'
             'Alternatively, create/update a firewall rule to allow access\n'
             'https://cloud.google.com/firewall/docs/using-firewalls#creating_firewall_rules'
            ))
      else:
        interface.add_ok(
            vm, (f'Connectivity to the instance {vm.name} from source\n'
                 f'{context.parameters.get(SRC_IP_FLAG)} is feasible'))
    # Check IAP if user wants to check it. alternatively,
    if context.parameters.get(TTI_FLAG):
      # Check IAP Firewall rule check since VM is not public
      result = vm.network.firewall.check_connectivity_ingress(
          src_ip=IAP_FW_VIP,
          ip_protocol='tcp',
          port=SSHD_PORT,
          target_service_account=vm.service_account,
          target_tags=vm.tags)
      if result.action == 'deny':
        response = interface.add_failed(
            vm,
            reason=
            (f'{vm.name} does not have ingress connections from IAP Virtual IP\n'
             f'{IAP_FW_VIP} to tcp:{SSHD_PORT} blocked by {result.matched_by_str}'
            ),
            remediation=
            ('Allow ingress traffic from the VIP range 35.235.240.0/20\n'
             'https://cloud.google.com/compute/docs/troubleshooting/'
             'troubleshooting-ssh-errors#diagnosis_methods_for_linux_and_windows_vms'
            ))
      elif result.action == 'allow':
        response = interface.add_ok(
            vm,
            reason=(
                f'{vm.name} can accept ingress connections from IAP Virtual IP\n'
                f'{IAP_FW_VIP} port tcp:{SSHD_PORT}'))

    # Check for pub IP instances
    if vm.is_public_machine():
      #TODO: check public issues
      result = vm.network.firewall.check_connectivity_ingress(
          src_ip=DEFAULT_FW_RULE,
          ip_protocol='tcp',
          port=SSHD_PORT,
          target_service_account=vm.service_account,
          target_tags=vm.tags)
      if result.action == 'deny':
        # Implied deny is a pass for IAP IP instances
        response = interface.add_failed(
            vm,
            reason=
            (f'Access from external IPs are not allowed {result.matched_by_str}'
            ),
            remediation=
            ('Consider using our recommended methods for connecting Compute Engine virtual\n'
             'machine (VM) instance through its internal IP address:\n'
             'https://cloud.google.com/compute/docs/connect/ssh-internal-ip'))
      else:
        interface.add_ok(
            vm, f'External connectivity to the instance {vm.name} is feasible')
    return response

  interface.execute_task(task)

  # TODO: Improve desicision section. The class concept can have a decision
  # fucntion which can take any context and return a Class or list of Classes
  # to execute
  interface.prompt(task=interface.DECISION, message='Checking OS Image...')
  if vm and not vm.is_windows_machine():
    interface.prompt(
        message='OS Image: Linux - Checking for linux related SSH issues...')
    return check_linux_guestos_kernel_status
  elif vm and vm.is_windows_machine():
    interface.prompt(
        message=
        'OS type Image: Windows - Checking for windows related SSH issues...')
    return check_windows_guestos_status


def check_linux_guestos_kernel_status(
    context: models.Context, interface: runbook.RunbookInteractionInterface):
  """Checking Linux Guest Kernel Status"""

  def task():
    response = None
    # All kernel failures.
    # We don't need fresh instance details so use global instance details
    instance_serial_log = gce.get_instance_serial_port_output(
        project_id=context.project_id,
        zone=context.parameters.get(ZONE_FLAG),
        instance_name=context.parameters.get(NAME_FLAG))
    if instance_serial_log:
      # TODO: Improve Search pattern to use cloud logging
      # but also return details for richer feeback to users
      kernel_errors = util.search_pattern_in_serial_logs(
          BOOT_ERROR_PATTERNS, instance_serial_log.contents)
      if kernel_errors:
        response = interface.add_failed(
            vm,
            reason=
            'The VM is experiencing a kernel panic, preventing it from booting up.',
            remediation=
            ('To resolve the kernel panic issue, follow these steps:\n'
             '1. Review general guidance on resolving kernel panic errors:\n'
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
             'support-maintenance-policy#out-of-scope_for_support'))
      elif not kernel_errors:
        interface.add_ok(
            vm,
            reason=
            'Linux OS is not experiencing kernel panic issue, GRUB issues\n'
            'or guest kernel dropping into emergency/maintenance mode')
    else:
      interface.add_uncertain(
          vm,
          reason='No serial logs data to examine',
          remediation=
          ('VM is up and running so check serial logs for possible issues.\n'
           'https://cloud.google.com/compute/docs/troubleshooting/viewing-serial-port-output\n'
           'if there is a Guest Kernel issue. Resolve the issue using our documentation\n'
           'https://cloud.google.com/compute/docs/troubleshooting/'
           'kernel-panic#resolve_the_kernel_panic_error\n\n'
           'NOTE: Faults within the Guest OS is Out of Support Scope\n'
           'See GCP support policy on Guest OS\n'
           'https://cloud.google.com/compute/docs/images/'
           'support-maintenance-policy#support-scope\n'
           'https://cloud.google.com/compute/docs/images/'
           'support-maintenance-policy#out-of-scope_for_support'))
    return response

  interface.execute_task(task)
  return verify_linux_sshd_working_correctly


GOOD_SSHD_PATTERNS = ['Starting OpenBSD Secure Shell server']
BAD_SSHD_PATTERNS = ['Failed to start OpenBSD Secure Shell server']


def verify_linux_sshd_working_correctly(
    context: models.Context, interface: runbook.RunbookInteractionInterface):
  """Checking SSHD and SSHGuard"""

  def task():
    response = None
    instance_serial_log = gce.get_instance_serial_port_output(
        project_id=context.project_id,
        zone=context.parameters.get(ZONE_FLAG),
        instance_name=context.parameters.get(NAME_FLAG))
    if instance_serial_log:
      result = util.search_pattern_in_serial_logs(GOOD_SSHD_PATTERNS,
                                                  instance_serial_log.contents)
      if result:
        interface.add_ok(vm, reason='SSHD started correctly')
      else:
        result = util.search_pattern_in_serial_logs(
            BAD_SSHD_PATTERNS, instance_serial_log.contents)
        if result:
          response = interface.add_failed(
              vm,
              reason='SSHD has failed in the VM',
              remediation=(
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
                  'support-maintenance-policy#out-of-scope_for_support'))
        else:
          response = interface.add_uncertain(
              vm,
              reason=
              'We cannot tell if SSHD is faulty or not. Manually investigate',
              remediation=(
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
                  'support-maintenance-policy#out-of-scope_for_support'))

      result = util.search_pattern_in_serial_logs(SSHGUARD_PATTERNS,
                                                  instance_serial_log.contents)
      if result:
        # todo: check user's src ip is not being blocked
        response = interface.add_failed(
            vm,
            reason=('SSHGuard is enabled and blocking IPs the VM'
                    'check to make sure your IP is not blocked.'),
            remediation=(
                'NOTE: SSHGuard related issues are Out of Support Scope\n'
                'See GCP support policy on Guest OS\n'
                'https://cloud.google.com/compute/docs/images/'
                'support-maintenance-policy#support-scope\n'
                'https://cloud.google.com/compute/docs/images/'
                'support-maintenance-policy#out-of-scope_for_support'))
      elif not result:
        interface.add_ok(vm, reason='SSHguard not blocking IPs on the VM')
    else:
      response = interface.add_uncertain(
          vm,
          reason='No Serial Logs data to examine',
          remediation=(
              'Manully investigate SSHDGuard via interactive serial console\n'
              'https://cloud.google.com/compute/docs/troubleshooting/'
              'troubleshooting-using-serial-console'))
    return response

  interface.execute_task(task)


def check_windows_guestos_status(
    context: models.Context, interface: runbook.RunbookInteractionInterface):
  """Checking windows Guest OS boot up status"""

  def task():
    global vm
    response = None
    # All kernel failures.
    vm = gce.get_instance(project_id=context.project_id,
                          zone=context.parameters.get(ZONE_FLAG),
                          instance_name=context.parameters.get(NAME_FLAG))

    instance_serial_log = gce.get_instance_serial_port_output(
        project_id=context.project_id,
        zone=context.parameters.get(ZONE_FLAG),
        instance_name=context.parameters.get(NAME_FLAG))

    if instance_serial_log:
      result = util.search_pattern_in_serial_logs(WINDOWS_ONLINE_READY,
                                                  instance_serial_log.contents,
                                                  operator='AND')
      if not result:
        response = interface.add_failed(
            vm,
            reason='Windows OS has not booted up correctly',
            remediation=
            ('Follow this documentation to ensure that VM is fully booted\n'
             'https://cloud.google.com/compute/docs/troubleshooting/troubleshooting-windows\n'
             'https://cloud.google.com/compute/docs/troubleshooting/'
             'troubleshooting-rdp#instance_ready'))
      elif result:
        interface.add_ok(
            vm,
            reason=
            'Windows OS serial logs show guest os is ready/has started correctly'
        )
    else:
      interface.add_uncertain(
          vm,
          reason='Insufficient evidence that Windows OS started correctly',
          remediation=
          ('Follow this documentation to ensure that VM is fully booted\n'
           'https://cloud.google.com/compute/docs/troubleshooting/troubleshooting-windows\n'
           'https://cloud.google.com/compute/docs/troubleshooting/'
           'troubleshooting-rdp#instance_ready'))
    return response

  interface.execute_task(task)
  return check_windows_sshd_metadata


# pylint: disable=unused-argument
def check_windows_sshd_metadata(context: models.Context,
                                interface: runbook.RunbookInteractionInterface):
  """Checking SSH in windows."""

  def task():
    response = None
    if vm.is_windows_machine(
    ) and not vm.is_metadata_enabled('enable-windows-ssh'):
      response = interface.add_failed(
          vm,
          reason=
          'SSH metadata is not enabled for the windows instance attempting to use SSHD',
          remediation=(
              'Enable SSH on Windows. Follow this guide:\n'
              'https://cloud.google.com/compute/docs/connect/windows-ssh#enable'
          ))
    else:
      interface.add_ok(vm, 'SSH is enabled for windows VM.')
    return response

  interface.execute_task(task)
  return check_sshd_setup_for_windows


def check_sshd_setup_for_windows(
    context: models.Context, interface: runbook.RunbookInteractionInterface):
  """Manually check ssh reqired Agents are running on the VM
      Check google-compute-engine-ssh is installed."""

  def task():
    response = None
    # TODO: check if event logs are export. For now use a manual approach
    if not config.get(AUTO):
      response = interface.prompt(
          task=interface.CONFIRMATION,
          message=(f'Is SSHD agent `google-compute-engine-ssh`'
                   f'installed on the VM {context.parameters.get(NAME_FLAG)}?'),
          options={
              'y': 'Yes',
              'n': 'No',
              'u': 'Unsure'
          })
    if response == 'u':
      response = interface.add_uncertain(
          vm,
          reason='Not certain that google-compute-engine-ssh agent is installed',
          remediation=
          ('RDP or use a startup script to verify/install agent availability\n'
           'https://cloud.google.com/compute/docs/connect/windows-ssh#startup-script'
          ))
    elif response == interface.YES:
      interface.add_ok(
          vm,
          'User confirmed google-compute-engine-ssh is installed for windows VM.'
      )
    elif response == interface.NO:
      response = interface.add_failed(
          vm,
          reason='Not certain that google-compute-engine-ssh agent is installed',
          remediation=
          ('Verify/install agent availability and proper configuration.\n'
           'https://cloud.google.com/compute/docs/connect/windows-ssh#startup-script'
          ))
    return response

  interface.execute_task(task=task)


# End is optional: Make check custom verification checks if required.
def end(context: models.Context,
        interface: runbook.RunbookInteractionInterface):
  if not config.get(AUTO):
    response = interface.prompt(
        task=interface.CONFIRMATION,
        message=
        f'Are you able to SSH into VM {context.parameters.get(NAME_FLAG)}?')
    if response == interface.NO:
      interface.prompt(message=(
          'Refer to our documentation on troubleshooting SSH\n'
          'https://cloud.google.com/compute/docs/trouble'
          'shooting/troubleshooting-ssh-errors\n\n'
          'Contact Google Cloud Support for further investigation.\n'
          'https://cloud.google.com/support/docs/customer-care-procedures\n'
          'Recommended: Submit the generated report to Google cloud support when opening a ticket.'
      ))
  interface.generate_report()
