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
"""Contains Resueable Steps for GCE related Diagnostic Trees"""
from typing import List

from gcpdiag import runbook
from gcpdiag.queries import gce, iam, monitoring
from gcpdiag.runbook import constants as const
from gcpdiag.runbook.gce import constants as gce_const
from gcpdiag.runbook.gce import parameters as gce_param
from gcpdiag.runbook.gce import util

UTILIZATION_THRESHOLD = 0.99
within_hours = 9
within_str = 'within %dh, d\'%s\'' % (within_hours,
                                      monitoring.period_aligned_now(5))


class GCEHighMemoryUtilization(runbook.Step):
  """Checking Memroy VM performance"""
  # Typcial Memory exhaustion logs in serial console.
  VM_OOM_PATTERN = [
      'Out of memory: Kill process', 'Kill process',
      'Memory cgroup out of memory'
  ]

  def execute(self):
    """Checking VM performance"""

    vm = gce.get_instance(project_id=self.op.get(gce_param.PROJECT_ID),
                          zone=self.op.get(gce_param.ZONE_FLAG),
                          instance_name=self.op.get(gce_param.NAME_FLAG))

    high_mem_usage = None

    if self.op.get(gce_param.OPS_AGENT_INSTALLED):
      high_mem_usage = monitoring.query(
          self.op.get(gce_param.PROJECT_ID), """
          fetch gce_instance
            | metric 'agent.googleapis.com/memory/percent_used'
            | filter (resource.instance_id == '{}')
            | group_by [resource.instance_id], 3m, [percent_used: mean(value.percent_used)]
            | filter (cast_units(percent_used,"")/100) >= {}
            | {}
          """.format(vm.id, UTILIZATION_THRESHOLD, within_str))

    else:
      if 'e2' in vm.machine_type():
        high_mem_usage = monitoring.query(
            self.op.get(gce_param.PROJECT_ID), """
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
          project_id=self.op.get(gce_param.PROJECT_ID),
          zone=self.op.get(gce_param.ZONE_FLAG),
          instance_name=self.op.get(gce_param.NAME_FLAG))

      if 'e2' not in vm.machine_type():
        if instance_serial_log:
          high_mem_usage = util.search_pattern_in_serial_logs(
              self.VM_OOM_PATTERN, instance_serial_log.contents)

    # Get Performance issues corrected.
    if high_mem_usage:
      self.interface.add_failed(
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
      self.interface.add_ok(
          vm,
          reason=(
              'The VM is operating within optimal memory utilization levels.'))


class GCEHighDiskUtilization(runbook.Step):
  """Checking VM Disk Utilization"""
  VM_DISK_SPACE_ERROR_PATTERN = [
      'No space left on device',
      'No usable temporary directory found in'
      # windows
      'disk is at or near capacity'
  ]

  def execute(self):
    """Checking VM Disk Utilization"""

    vm = gce.get_instance(project_id=self.op.get(gce_param.PROJECT_ID),
                          zone=self.op.get(gce_param.ZONE_FLAG),
                          instance_name=self.op.get(gce_param.NAME_FLAG))

    high_disk_usage = None

    if self.op.get(gce_param.OPS_AGENT_INSTALLED):
      high_disk_usage = monitoring.query(
          self.op.get(gce_param.PROJECT_ID), """
        fetch gce_instance
            | metric 'agent.googleapis.com/disk/percent_used'
            | filter (resource.instance_id == '{}')
            | group_by [resource.instance_id], 3m, [percent_used: mean(value.percent_used)]
            | filter (cast_units(percent_used,"")/100) >= {}
            | {}
          """.format(vm.id, UTILIZATION_THRESHOLD, within_str))
    else:
      # fallback on serial logs to see if there are OOM logs
      instance_serial_log = gce.get_instance_serial_port_output(
          project_id=self.op.get(gce_param.PROJECT_ID),
          zone=self.op.get(gce_param.ZONE_FLAG),
          instance_name=self.op.get(gce_param.NAME_FLAG))

      if instance_serial_log:
        # All VM types + e2
        high_disk_usage = util.search_pattern_in_serial_logs(
            self.VM_DISK_SPACE_ERROR_PATTERN, instance_serial_log.contents)

    if high_disk_usage:
      self.interface.add_failed(
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
      self.interface.add_ok(
          vm,
          ('The VM is operating within optimal disk space utilization levels.'))


class GCEHighCPUPerformance(runbook.Step):
  """Diagnose VM CPU performance"""

  def execute(self):
    """Checking VM CPU is performning at optimal levels"""

    vm = gce.get_instance(project_id=self.op.get(gce_param.PROJECT_ID),
                          zone=self.op.get(gce_param.ZONE_FLAG),
                          instance_name=self.op.get(gce_param.NAME_FLAG))
    high_cpu_usage = None

    if self.op.get(gce_param.OPS_AGENT_INSTALLED):
      high_cpu_usage = monitoring.query(
          self.op.get(gce_param.PROJECT_ID), """
          fetch gce_instance
            | metric 'agent.googleapis.com/cpu/utilization'
            | filter (resource.instance_id == '{}')
            | group_by [resource.instance_id], 3m, [value_utilization_mean: mean(value.utilization)]
            | filter (cast_units(value_utilization_mean,"")/100) >= {}
            | {}
          """.format(vm.id, UTILIZATION_THRESHOLD, within_str))
    else:
      # use CPU utilization visible to the hypervisor
      high_cpu_usage = monitoring.query(
          self.op.get(gce_param.PROJECT_ID), """
            fetch gce_instance
              | metric 'compute.googleapis.com/instance/cpu/utilization'
              | filter (resource.instance_id == '{}')
              | group_by [resource.instance_id], 3m, [value_utilization_max: max(value.utilization)]
              | filter value_utilization_max >= {}
              | {}
            """.format(vm.id, UTILIZATION_THRESHOLD, within_str))
    # Get Performance issues corrected.
    if high_cpu_usage:
      self.interface.add_failed(
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
      self.interface.add_ok(
          vm,
          reason=('The VM is operating within optimal CPU utilization levels.'))


class GCEInRunningState(runbook.Step):
  """Checking VM lifecycle state"""

  def execute(self):
    """Checking VM lifecycle in Running state"""
    vm = gce.get_instance(project_id=self.op.get(gce_param.PROJECT_ID),
                          zone=self.op.get(gce_param.ZONE_FLAG),
                          instance_name=self.op.get(gce_param.NAME_FLAG))
    if vm and vm.is_running():
      self.interface.add_ok(vm,
                            reason=f'VM: {vm.name} is in a {vm.status} state.')
    else:
      # Register evaluation. Later used in generating a report for support.
      self.interface.add_failed(
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


class GCESerialLogsCheck(runbook.Step):
  """Examine GCE Serial Logs for common patterns"""

  # Typical logs of a fully booted windows VM
  GOOD_PATTERN: List = []
  GOOD_PATTERN_OPERATOR = 'OR'
  BAD_PATTERN: List = []
  BAD_PATTERN_OPERATOR = 'OR'

  def set_prompts(self):
    self.prompts = {
        const.FAILURE_REASON:
            'Bad application logs detected',
        const.FAILURE_REMEDIATION:
            ('Investigate issue issue using our documentation\n'
             'https://cloud.google.com/compute/docs/troubleshooting'),
        const.SUCCESS_REASON:
            'Desired application logs are present in the serial logs',
        const.UNCERTAIN_REASON: ('No serial logs data to examine'),
        const.UNCERTAIN_REMEDIATION:
            ('Investigate issue  using our documentation\n'
             'https://cloud.google.com/compute/docs/troubleshooting'),
        const.SKIPPED_REASON:
            'No logs were found for the instance',
    }

  def execute(self):
    """Check GCE Serial Logs for common application patterns"""
    # All kernel failures.
    good_pattern_detected = False
    bad_pattern_detected = False
    vm = gce.get_instance(project_id=self.op.get(gce_param.PROJECT_ID),
                          zone=self.op.get(gce_param.ZONE_FLAG),
                          instance_name=self.op.get(gce_param.NAME_FLAG))

    instance_serial_log = gce.get_instance_serial_port_output(
        project_id=self.op.get(gce_param.PROJECT_ID),
        zone=self.op.get(gce_param.ZONE_FLAG),
        instance_name=self.op.get(gce_param.NAME_FLAG))

    if instance_serial_log:
      if self.GOOD_PATTERN:
        good_pattern_detected = util.search_pattern_in_serial_logs(
            self.GOOD_PATTERN,
            instance_serial_log.contents,
            operator=self.GOOD_PATTERN_OPERATOR)
        if good_pattern_detected:
          self.interface.add_ok(vm,
                                reason=self.prompts.get(const.SUCCESS_REASON))
      elif self.BAD_PATTERN:
        # Check for bad patterns
        bad_pattern_detected = util.search_pattern_in_serial_logs(
            self.BAD_PATTERN,
            instance_serial_log.contents,
            operator=self.BAD_PATTERN_OPERATOR)
        if bad_pattern_detected:
          self.interface.add_failed(
              vm,
              reason=self.prompts.get(const.FAILURE_REASON),
              remediation=self.prompts.get(const.FAILURE_REMEDIATION))
      if not good_pattern_detected and not bad_pattern_detected:
        self.interface.add_uncertain(
            vm,
            reason=self.prompts.get(const.UNCERTAIN_REASON),
            remediation=self.prompts.get(const.UNCERTAIN_REMEDIATION))
    else:
      self.interface.add_skipped(vm,
                                 reason=self.prompts.get(const.SKIPPED_REASON))


class UserCanViewCloudConsole(runbook.Step):
  """Step to check for Compute Project Get permission"""
  console_user_permission = 'compute.projects.get'

  def execute(self):
    """User has permission to View Cloud Console"""
    vm = gce.get_instance(project_id=self.op.get(gce_param.PROJECT_ID),
                          zone=self.op.get(gce_param.ZONE_FLAG),
                          instance_name=self.op.get(gce_param.NAME_FLAG))
    iam_policy = iam.get_project_policy(vm.project_id)

    auth_user = self.op.get(gce_param.PRINCIPAL_FLAG)
    # Check user has permisssion to access the VM in the first place
    if iam_policy.has_permission(auth_user, self.console_user_permission):
      self.interface.add_ok(
          resource=iam_policy,
          reason='User has permission to View the Console and compute resources'
      )
    else:
      self.interface.add_failed(
          iam_policy,
          f'To use the Google Cloud console to access Compute Engine, e.g. SSH in browser,\n'
          f'principal must have the {self.console_user_permission} permission.',
          'Refer to the documentation:\n'
          'https://cloud.google.com/compute/docs/access/iam#console_permission')


class GCEBooleanMetadataCheck(runbook.Step):
  """General class for checking VM metadata."""
  # key to inspect
  METADATA_KEY: str
  # desired value.
  METADATA_VALUE: bool

  def execute(self):
    """Checking metadata."""
    vm = gce.get_instance(project_id=self.op.get(gce_param.PROJECT_ID),
                          zone=self.op.get(gce_param.ZONE_FLAG),
                          instance_name=self.op.get(gce_param.NAME_FLAG))
    if gce_const.BOOL_VALUES[vm.get_metadata(
        self.METADATA_KEY)] == self.METADATA_VALUE:
      self.interface.add_ok(vm, self.prompts[const.SUCCESS_REASON])
    else:
      self.interface.add_failed(
          vm,
          reason=self.prompts[const.FAILURE_REASON],
          remediation=self.prompts[const.FAILURE_REMEDIATION])

  def set_prompts(self):
    self.prompts = {
        const.FAILURE_REASON:
            'Desired metadata value is not set for the metadata key',
        const.FAILURE_REMEDIATION:
            ('Update the metadata to the correct value\n'
             'https://cloud.google.com/compute/docs/metadata/'
             'setting-custom-metadata#set-custom-metadata'),
        const.SUCCESS_REASON:
            'Desired Metadata Configuration is present',
    }


class IngressTrafficAllowedForGCEInstance(runbook.Step):
  """Checking VPC network"""

  def set_prompts(self):
    self.prompts = {
        gce_const.FAILURE_REASON:
            ('Ingress Traffic from source IP "{}", for'
             'protocol:{} port:{} to instance {} is not allowed by: {}'),
        gce_const.FAILURE_REMEDIATION: (
            'If connecting to a non-public VM and do not wish to allow \n'
            'external access, choose one of the following connection options for VMs\n'
            'https://cloud.google.com/compute/docs/connect/ssh-internal-ip\n\n'
            'Alternatively, create/update a firewall rule to allow access\n'
            'https://cloud.google.com/firewall/docs/using-firewalls#creating_firewall_rules'
        ),
        gce_const.SUCCESS_REASON:
            ('Ingress Traffic from source IP/CIDR {}, '
             '{}:{}  to the GCE instance {} is allow by: {}')
    }

  def execute(self):
    """Checking Ingress Traffic via GCP VPC network"""
    vm = gce.get_instance(project_id=self.op.get(gce_param.PROJECT_ID),
                          zone=self.op.get(gce_param.ZONE_FLAG),
                          instance_name=self.op.get(gce_param.NAME_FLAG))
    result = None
    result = vm.network.firewall.check_connectivity_ingress(
        src_ip=self.op.get(gce_param.SRC_IP_FLAG),
        ip_protocol=self.op.get(gce_param.PROTOCOL_TYPE),
        port=gce_const.DEFAULT_SSHD_PORT,
        target_service_account=vm.service_account,
        target_tags=vm.tags)
    if result.action == 'deny':
      self.interface.add_failed(
          vm,
          reason=(self.prompts.get(gce_const.FAILURE_REASON).format(
              self.op.get(gce_param.SRC_IP_FLAG),
              self.op.get(gce_param.PROTOCOL_TYPE),
              self.op.get(gce_param.PORT_FLAG), vm.name,
              result.matched_by_str)),
          remediation=self.prompts.get(const.FAILURE_REMEDIATION))
    elif result.action == 'allow':
      self.interface.add_ok(vm,
                            (self.prompts.get(gce_const.FAILURE_REASON).format(
                                self.op.get(gce_param.SRC_IP_FLAG),
                                self.op.get(gce_param.PROTOCOL_TYPE),
                                self.op.get(gce_param.PORT_FLAG), vm.name,
                                result.matched_by_str)))
