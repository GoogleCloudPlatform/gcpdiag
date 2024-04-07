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

import logging
import math
from typing import Any, List

from gcpdiag import runbook
from gcpdiag.queries import gce, iam, monitoring
from gcpdiag.runbook import op
from gcpdiag.runbook.gce import flags, util

UTILIZATION_THRESHOLD = 0.99
within_hours = 8
within_str = 'within %dh, d\'%s\'' % (within_hours,
                                      monitoring.period_aligned_now(5))


class HighVmMemoryUtilization(runbook.Step):
  """Diagnoses high memory utilization issues in a Compute Engine VM.

  This step evaluates memory usage through available monitoring data or, as a fallback, scans serial
  logs for Out of Memory (OOM) indicators. It distinguishes between VMs which has exported metrics
  and those without, and employs a different strategy for 'e2' machine types to accurately assess
  memory utilization.
  """
  template = 'vm_performance::high_memory_utilization'
  # Typcial Memory exhaustion logs in serial console.
  oom_pattern = [
      'Out of memory: Kill process', 'Kill process',
      'Memory cgroup out of memory'
  ]

  def execute(self):
    """Verifying VM memory utilization is within optimal levels..."""

    vm = gce.get_instance(project_id=op.get(flags.PROJECT_ID),
                          zone=op.get(flags.ZONE),
                          instance_name=op.get(flags.NAME))

    mem_usage_metrics = None

    if op.get(flags.OPS_AGENT_EXPORTING_METRICS):
      mem_usage_metrics = monitoring.query(
          op.get(flags.PROJECT_ID), """
          fetch gce_instance
            | metric 'agent.googleapis.com/memory/percent_used'
            | filter (resource.instance_id == '{}')
            | group_by [resource.instance_id], 3m, [percent_used: mean(value.percent_used)]
            | filter (cast_units(percent_used,"")/100) >= {}
            | {}
          """.format(vm.id, UTILIZATION_THRESHOLD, within_str))

    else:
      if 'e2' in vm.machine_type():
        mem_usage_metrics = monitoring.query(
            op.get(flags.PROJECT_ID), """
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
          project_id=op.get(flags.PROJECT_ID),
          zone=op.get(flags.ZONE),
          instance_name=op.get(flags.NAME))

      if 'e2' not in vm.machine_type():
        if instance_serial_log:
          mem_usage_metrics = util.search_pattern_in_serial_logs(
              self.oom_pattern, instance_serial_log.contents)

    # Get Performance issues corrected.
    if mem_usage_metrics:
      op.add_failed(vm,
                    reason=op.prep_msg(op.FAILURE_REASON),
                    remediation=op.prep_msg(op.FAILURE_REMEDIATION))
    else:
      op.add_ok(vm, reason=op.prep_msg(op.SUCCESS_REASON))


class HighVmDiskUtilization(runbook.Step):
  """Assesses disk utilization on a VM, aiming to identify high usage that could impact performance.

  This step leverages monitoring data if the Ops Agent is exporting disk usage metrics.
  Alternatively, it scans the VM's serial port output for common disk space error messages.
  This approach ensures comprehensive coverage across different scenarios,
  including VMs without metrics data.
  """
  template = 'vm_performance::high_disk_utilization'

  disk_exhaustion_error_pattern = [
      'No space left on device',
      'No usable temporary directory found in'
      # windows
      'disk is at or near capacity'
  ]

  def execute(self):
    """Verifying VM's Boot disk space utilization is within optimal levels."""

    vm = gce.get_instance(project_id=op.get(flags.PROJECT_ID),
                          zone=op.get(flags.ZONE),
                          instance_name=op.get(flags.NAME))

    disk_usage_metrics = None

    if op.get(flags.OPS_AGENT_EXPORTING_METRICS):
      disk_usage_metrics = monitoring.query(
          op.get(flags.PROJECT_ID), """
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
          project_id=op.get(flags.PROJECT_ID),
          zone=op.get(flags.ZONE),
          instance_name=op.get(flags.NAME))

      if instance_serial_log:
        # All VM types + e2
        disk_usage_metrics = util.search_pattern_in_serial_logs(
            self.disk_exhaustion_error_pattern, instance_serial_log.contents)

      if disk_usage_metrics:
        op.add_failed(vm,
                      reason=op.prep_msg(op.FAILURE_REASON),
                      remediation=op.prep_msg(op.FAILURE_REMEDIATION))
      else:
        op.add_ok(vm, reason=op.prep_msg(op.SUCCESS_REASON))


class HighVmCpuUtilization(runbook.Step):
  """Evaluates the CPU of a VM for high utilization that might indicate performance issues.

  This step determines whether the CPU utilization of the VM exceeds a predefined threshold,
  indicating potential performance degradation. It utilizes metrics from the Ops Agent if installed,
  or hypervisor-visible metrics as a fallback, to accurately assess CPU performance and identify any
  issues requiring attention.
  """

  template = 'vm_performance::high_cpu_utilization'

  def execute(self):
    """Verifying VM CPU utilization is within optimal levels"""

    vm = gce.get_instance(project_id=op.get(flags.PROJECT_ID),
                          zone=op.get(flags.ZONE),
                          instance_name=op.get(flags.NAME))
    cpu_usage_metrics = None

    if op.get(flags.OPS_AGENT_EXPORTING_METRICS):
      cpu_usage_metrics = monitoring.query(
          op.get(flags.PROJECT_ID), """
          fetch gce_instance
            | metric 'agent.googleapis.com/cpu/utilization'
            | filter (resource.instance_id == '{}')
            | group_by [resource.instance_id], 3m, [value_utilization_mean: mean(value.utilization)]
            | filter (cast_units(value_utilization_mean,"")/100) >= {}
            | {}
          """.format(vm.id, UTILIZATION_THRESHOLD, within_str))
    else:
      # use CPU utilization visible to the hypervisor
      cpu_usage_metrics = monitoring.query(
          op.get(flags.PROJECT_ID), """
            fetch gce_instance
              | metric 'compute.googleapis.com/instance/cpu/utilization'
              | filter (resource.instance_id == '{}')
              | group_by [resource.instance_id], 3m, [value_utilization_max: max(value.utilization)]
              | filter value_utilization_max >= {}
              | {}
            """.format(vm.id, UTILIZATION_THRESHOLD, within_str))
    # Get Performance issues corrected.
    if cpu_usage_metrics:
      op.add_failed(vm,
                    reason=op.prep_msg(op.FAILURE_REASON),
                    remediation=op.prep_msg(op.FAILURE_REMEDIATION))
    else:
      op.add_ok(vm, reason=op.prep_msg(op.SUCCESS_REASON))


class VmLifecycleState(runbook.Step):
  """Validates that a specified VM is in the 'RUNNING' state.

  This step is crucial for confirming the VM's availability and operational readiness.
  It checks the VM's lifecycle state and reports success if the VM is running or fails the
  check if the VM is in any other state, providing detailed status information for
  troubleshooting.
  """

  template = 'vm_attributes::running'

  def execute(self):
    """Verifying VM is in the RUNNING state..."""
    vm = gce.get_instance(project_id=op.get(flags.PROJECT_ID),
                          zone=op.get(flags.ZONE),
                          instance_name=op.get(flags.NAME))
    if vm and vm.is_running:
      op.add_ok(vm,
                reason=op.prep_msg(op.SUCCESS_REASON,
                                   vm_name=vm.name,
                                   status=vm.status))
    else:
      op.add_failed(vm,
                    reason=op.prep_msg(op.FAILURE_REASON,
                                       vm_name=vm.name,
                                       status=vm.status),
                    remediation=op.prep_msg(op.FAILURE_REMEDIATION,
                                            vm_name=vm.name,
                                            status=vm.status))


class VmSerialLogsCheck(runbook.Step):
  """Searches for predefined good or bad patterns in the serial logs of a GCE VM.

  This diagnostic step checks the VM's serial logs for patterns that are indicative of successful
  operations ('GOOD_PATTERN') or potential issues ('BAD_PATTERN'). Based on the presence of these
  patterns, the step categorizes the VM's status as 'OK', 'Failed', or 'Uncertain'.
  """

  template = 'vm_serial_log::default'

  # Typical logs of a fully booted windows VM
  positive_pattern: List = []
  positive_pattern_operator = 'OR'
  negative_pattern: List = []
  negative_pattern_operator = 'OR'

  def execute(self):
    """Analyzing serial logs for predefined patterns..."""
    # All kernel failures.
    good_pattern_detected = False
    bad_pattern_detected = False
    vm = gce.get_instance(project_id=op.get(flags.PROJECT_ID),
                          zone=op.get(flags.ZONE),
                          instance_name=op.get(flags.NAME))

    instance_serial_log = gce.get_instance_serial_port_output(
        project_id=op.get(flags.PROJECT_ID),
        zone=op.get(flags.ZONE),
        instance_name=op.get(flags.NAME))

    if instance_serial_log:
      if self.positive_pattern:
        good_pattern_detected = util.search_pattern_in_serial_logs(
            self.positive_pattern,
            instance_serial_log.contents,
            operator=self.positive_pattern_operator)
        if good_pattern_detected:
          op.add_ok(vm, reason=op.prep_msg(op.SUCCESS_REASON))
      elif self.negative_pattern:
        # Check for bad patterns
        bad_pattern_detected = util.search_pattern_in_serial_logs(
            self.negative_pattern,
            instance_serial_log.contents,
            operator=self.negative_pattern_operator)
        if bad_pattern_detected:
          op.add_failed(vm,
                        reason=op.prep_msg(op.FAILURE_REASON),
                        remediation=op.prep_msg(op.FAILURE_REMEDIATION))
      if not good_pattern_detected and not bad_pattern_detected:
        op.add_uncertain(vm,
                         reason=op.prep_msg(op.UNCERTAIN_REASON),
                         remediation=op.prep_msg(op.UNCERTAIN_REMEDIATION))
    else:
      op.add_skipped(vm, reason=op.prep_msg(op.SKIPPED_REASON))


class AuthPrincipalCloudConsolePermissionCheck(runbook.Step):
  """Validates if the user has the 'compute.projects.get' permission within the GCP Project.

  This permission is essential to be able to use SSH in browser and
  viewing the Compute Engine resources in the Cloud Console.
  """

  console_user_permission = 'compute.projects.get'
  template = 'gce_permissions::console_view_permission'

  def execute(self):
    """Verifying user access to Cloud Console..."""
    iam_policy = iam.get_project_policy(op.get(flags.PROJECT_ID))

    auth_user = op.get(flags.PRINCIPAL)
    # Check user has permisssion to access the VM in the first place
    if iam_policy.has_permission(auth_user, self.console_user_permission):
      op.add_ok(resource=iam_policy, reason=op.prep_msg(op.SUCCESS_REASON))
    else:
      op.add_failed(iam_policy,
                    reason=op.prep_msg(op.FAILURE_REASON),
                    remediation=op.prep_msg(op.FAILURE_REMEDIATION))


class VmMetadataCheck(runbook.Step):
  """Validates a specific boolean metadata key-value pair on a GCE VM instance.

  This step checks if the VM's metadata contains a specified key with the expected boolean value,
  facilitating configuration verification and compliance checks."""

  template: str = 'vm_metadata::default'
  # key to inspect
  metadata_key: str
  # desired value.
  expected_value: Any
  # the expected_metadata_value type
  # default is bool
  expected_value_type: type = bool

  def is_expected_md_value(self, actual_value):
    """
    Compare a VM's metadata value with an expected value, converting types as necessary.

    Parameters:
    - vm: The VM object containing metadata.
    - actual_value: The actual value present on resource.

    Returns:
    - True if the acutual metadata value matches the expected value, False otherwise.
    """
    # Determine the type of the expected value
    if isinstance(self.expected_value, bool):
      # Convert the string metadata value to a bool for comparison
      return op.BOOL_VALUES.get(actual_value, False) == self.expected_value
    elif isinstance(self.expected_value, str):
      # Directly compare string values
      return actual_value == self.expected_value
    elif isinstance(self.expected_value, str):
      # Directly compare string values
      return actual_value == self.expected_value
    elif isinstance(self.expected_value, (int, float)):
      # use isclose math to compare int and float
      return math.isclose(actual_value, self.expected_value)
    # Note: Implement other datatype checks if required.
    else:
      # Handle other types or raise an error
      logging.error(
          'Error while processing %s: Unsupported expected value type: %s',
          self.__class__.__name__, type(self.expected_value))
      raise ValueError('Unsupported Type')

  def execute(self):
    """Verifying VM metadata value..."""
    vm = gce.get_instance(project_id=op.get(flags.PROJECT_ID),
                          zone=op.get(flags.ZONE),
                          instance_name=op.get(flags.NAME))

    if self.is_expected_md_value(vm.get_metadata(self.metadata_key)):
      op.add_ok(
          vm,
          op.prep_msg(op.SUCCESS_REASON,
                      metadata_key=self.metadata_key,
                      expected_value=self.expected_value,
                      expected_value_type=self.expected_value_type))
    else:
      op.add_failed(
          vm,
          reason=op.prep_msg(op.FAILURE_REASON,
                             metadata_key=self.metadata_key,
                             expected_value=self.expected_value,
                             expected_value_type=self.expected_value_type),
          remediation=op.prep_msg(op.FAILURE_REMEDIATION,
                                  metadata_key=self.metadata_key,
                                  expected_value=self.expected_value,
                                  expected_value_type=self.expected_value_type))


class GceVpcConnectivityCheck(runbook.Step):
  """Checks whether ingress or egress traffic is allowed to a GCE VM from a specified source IP.

  Evaluates VPC firewall rules to verify if a GCE VM permits ingress or egress traffic from a
  designated source IP through a specified port and protocol.
  """
  traffic = None

  def execute(self):
    """Evaluating VPC network traffic rules..."""
    vm = gce.get_instance(project_id=op.get(flags.PROJECT_ID),
                          zone=op.get(flags.ZONE),
                          instance_name=op.get(flags.NAME))
    result = None
    if self.traffic == 'ingress':
      result = vm.network.firewall.check_connectivity_ingress(
          src_ip=op.get(flags.SRC_IP),
          ip_protocol=op.get(flags.PROTOCOL_TYPE),
          port=op.get(flags.PORT),
          target_service_account=vm.service_account,
          target_tags=vm.tags)
    if self.traffic == 'egress':
      result = vm.network.firewall.check_connectivity_egress(
          src_ip=vm.network_ips,
          ip_protocol=op.get(flags.PROTOCOL_TYPE),
          port=op.get(flags.PORT),
          target_service_account=vm.service_account,
          target_tags=vm.tags)
    if result.action == 'deny':
      op.add_failed(vm,
                    reason=op.prep_msg(op.FAILURE_REASON,
                                       address=op.get(flags.SRC_IP),
                                       protocol=op.get(flags.PROTOCOL_TYPE),
                                       port=op.get(flags.PORT),
                                       name=vm.name,
                                       result=result.matched_by_str),
                    remediation=op.prep_msg(op.FAILURE_REMEDIATION))
    elif result.action == 'allow':
      op.add_ok(
          vm,
          op.prep_msg(op.SUCCESS_REASON,
                      address=op.get(flags.SRC_IP),
                      protocol=op.get(flags.PROTOCOL_TYPE),
                      port=op.get(flags.PORT),
                      name=vm.name,
                      result=result.matched_by_str))
