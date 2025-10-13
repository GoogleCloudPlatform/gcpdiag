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
"""Contains Reusable Steps for GCE related Diagnostic Trees"""

import logging
import math
import operator as operator_mod
import re
from datetime import datetime
from typing import Any, List, Optional, Set

import apiclient.errors
from boltons.iterutils import get_path

from gcpdiag import runbook, utils
from gcpdiag.queries import gce, logs, monitoring
from gcpdiag.runbook import exceptions as runbook_exceptions
from gcpdiag.runbook import op
from gcpdiag.runbook import util as runbook_util
from gcpdiag.runbook.gce import constants, util
from gcpdiag.runbook.gcp import flags
from gcpdiag.runbook.iam import flags as iam_flags
from gcpdiag.runbook.iam import generalized_steps as iam_gs
from gcpdiag.runbook.logs import generalized_steps as logs_gs

UTILIZATION_THRESHOLD = 0.95


def _get_operator_fn(op_str: str):
  """Maps an operator string to a function from the operator module."""
  operators = {
      'eq': operator_mod.eq,
      'ne': operator_mod.ne,
      'lt': operator_mod.lt,
      'le': operator_mod.le,
      'gt': operator_mod.gt,
      'ge': operator_mod.ge,
  }
  if op_str not in operators:
    raise ValueError(
        f"Unsupported operator: '{op_str}'. Supported operators are: "
        f"{list(operators.keys()) + ['contains', 'matches']}")
  return operators[op_str]


def _resolve_expected_value(value_str: str) -> Any:
  """Resolves expected value, handling 'ref:' prefix."""
  if value_str.startswith('ref:'):
    const_name = value_str[4:]
    resolved_value = getattr(constants, const_name, None)
    if resolved_value is None:
      raise ValueError(f"Could not resolve constant reference: '{value_str}'. "
                       f"Ensure '{const_name}' is defined in gce/constants.py.")
    return resolved_value
  return value_str


def _check_condition(actual_value: Any, expected_value: Any,
                     op_str: str) -> bool:
  """Compares actual and expected values using the specified operator."""
  # Handle collection/regex operators first
  if op_str == 'contains':
    if hasattr(actual_value, '__contains__'):
      return expected_value in actual_value
    else:
      return False
  if op_str == 'matches':
    try:
      if isinstance(actual_value, (list, set, tuple)):
        return any(
            re.search(str(expected_value), str(item)) for item in actual_value)
      else:
        return bool(re.search(str(expected_value), str(actual_value)))
    except re.error as e:
      raise ValueError(
          f"Invalid regex pattern provided in expected_value: '{expected_value}'"
      ) from e

  op_fn = _get_operator_fn(op_str)
  try:
    # Attempt to convert to bool if expected is bool
    if isinstance(expected_value, bool):
      actual_value = op.BOOL_VALUES.get(str(actual_value).lower())
    # Attempt to convert to numeric if expected is numeric
    elif isinstance(expected_value, (int, float)):
      try:
        actual_value = type(expected_value)(actual_value)
      except (ValueError, TypeError):
        pass  # If conversion fails, compare as is
    return op_fn(actual_value, expected_value)
  except TypeError:
    # If types are incompatible for comparison, consider it a mismatch
    return False


class HighVmMemoryUtilization(runbook.Step):
  """Diagnoses high memory utilization issues in a Compute Engine VM.

  This step evaluates memory usage through available monitoring data or, as a fallback, scans serial
  logs for Out of Memory (OOM) indicators. It distinguishes between VMs which has exported metrics
  and those without, and employs a different strategy for 'e2' machine types to accurately assess
  memory utilization.
  """
  template = 'vm_performance::high_memory_utilization'

  project_id: Optional[str] = None
  zone: Optional[str] = None
  instance_name: Optional[str] = None
  vm: Optional[gce.Instance] = None
  serial_console_file = None

  # Typical Memory exhaustion logs in serial console.

  def execute(self):
    """Verify VM memory utilization is within optimal levels."""

    if self.vm:
      vm = self.vm
      self.project_id = vm.project_id
      self.zone = vm.zone
      self.instance_name = vm.name
    else:
      vm = gce.get_instance(
          project_id=self.project_id,
          zone=self.zone,
          instance_name=self.instance_name,
      )

    if not vm:
      op.add_skipped(
          None,
          reason=(f'VM instance {self.instance_name} not found in project'
                  f' {self.project_id} zone {self.zone}'),
      )
      return

    start_formatted_string = op.get(
        flags.START_TIME).strftime('%Y/%m/%d %H:%M:%S')
    end_formatted_string = op.get(flags.END_TIME).strftime('%Y/%m/%d %H:%M:%S')
    within_str = f'within d\'{start_formatted_string}\', d\'{end_formatted_string}\''

    mark_no_ops_agent = False

    mem_usage_metrics = None

    if util.ops_agent_installed(self.project_id, vm.id):
      mem_usage_metrics = monitoring.query(
          self.project_id, """
          fetch gce_instance
            | metric 'agent.googleapis.com/memory/percent_used'
            | filter (resource.instance_id == '{}')
            | group_by [resource.instance_id], 3m, [percent_used: mean(value.percent_used)]
            | filter (cast_units(percent_used,"")/100) >= {}
            | {}
          """.format(vm.id, UTILIZATION_THRESHOLD, within_str))
    elif 'e2' in vm.machine_type():
      mem_usage_metrics = monitoring.query(
          self.project_id, """
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
    else:
      mark_no_ops_agent = True
      op.info(
          f'VM instance {vm.id} not export memory metrics. Falling back on serial logs'
      )

    if mem_usage_metrics:
      op.add_failed(vm,
                    reason=op.prep_msg(op.FAILURE_REASON,
                                       full_resource_path=vm.full_path),
                    remediation=op.prep_msg(op.FAILURE_REMEDIATION))
    elif mark_no_ops_agent:
      op.add_skipped(vm,
                     reason=op.prep_msg(op.SKIPPED_REASON,
                                        full_resource_path=vm.full_path))
    else:
      op.add_ok(vm,
                reason=op.prep_msg(op.SUCCESS_REASON,
                                   full_resource_path=vm.full_path))

    # Checking for OOM related errors
    oom_errors = VmSerialLogsCheck()
    oom_errors.vm = vm
    oom_errors.serial_console_file = self.serial_console_file
    oom_errors.template = 'vm_performance::high_memory_usage_logs'
    oom_errors.negative_pattern = constants.OOM_PATTERNS
    self.add_child(oom_errors)


class HighVmDiskUtilization(runbook.Step):
  """Assesses disk utilization on a VM, aiming to identify high usage that could impact performance.

  This step leverages monitoring data if the Ops Agent is exporting disk usage metrics.
  Alternatively, it scans the VM's serial port output for common disk space error messages.
  This approach ensures comprehensive coverage across different scenarios,
  including VMs without metrics data.
  """
  template = 'vm_performance::high_disk_utilization'

  project_id: Optional[str] = None
  zone: Optional[str] = None
  instance_name: Optional[str] = None
  vm: Optional[gce.Instance] = None
  serial_console_file: str = ''

  def execute(self):
    """Verify VM's Boot disk space utilization is within optimal levels."""

    if self.vm:
      vm = self.vm
      self.project_id = vm.project_id
      self.zone = vm.zone
      self.instance_name = vm.name
    else:
      vm = gce.get_instance(
          project_id=self.project_id,
          zone=self.zone,
          instance_name=self.instance_name,
      )

    if not vm:
      op.add_skipped(
          None,
          reason=(f'VM instance {self.instance_name} not found in project'
                  f' {self.project_id} zone {self.zone}'),
      )
      return

    start_formatted_string = op.get(
        flags.START_TIME).strftime('%Y/%m/%d %H:%M:%S')
    end_formatted_string = op.get(flags.END_TIME).strftime('%Y/%m/%d %H:%M:%S')
    within_str = (
        f"within d'{start_formatted_string}', d'{end_formatted_string}'")

    mark_no_ops_agent = False

    disk_usage_metrics = None

    if util.ops_agent_installed(self.project_id, vm.id):
      disk_usage_metrics = monitoring.query(
          self.project_id, """
          fetch gce_instance
            | metric 'agent.googleapis.com/disk/percent_used'
            | filter (resource.instance_id == '{}' && metric.device !~ '/dev/loop.*' && metric.state == 'used')
            | group_by [resource.instance_id], 3m, [percent_used: mean(value.percent_used)]
            | filter (cast_units(percent_used,"")/100) >= {}
            | {}
          """.format(vm.id, UTILIZATION_THRESHOLD, within_str))
      op.add_metadata('Disk Utilization Threshold (fraction of 1)',
                      UTILIZATION_THRESHOLD)
    else:
      mark_no_ops_agent = True

    if disk_usage_metrics:
      op.add_failed(vm,
                    reason=op.prep_msg(op.FAILURE_REASON),
                    remediation=op.prep_msg(op.FAILURE_REMEDIATION,
                                            full_resource_path=vm.full_path))
    elif mark_no_ops_agent:
      op.add_skipped(vm,
                     reason=op.prep_msg(op.SKIPPED_REASON,
                                        full_resource_path=vm.full_path))
      # Fallback to check for filesystem utilization related messages in Serial logs
      fs_util = VmSerialLogsCheck()
      fs_util.vm = vm
      fs_util.serial_console_file = self.serial_console_file
      fs_util.template = 'vm_performance::high_disk_utilization_error'
      fs_util.negative_pattern = constants.DISK_EXHAUSTION_ERRORS
      self.add_child(fs_util)
    else:
      op.add_ok(vm,
                reason=op.prep_msg(op.SUCCESS_REASON,
                                   full_resource_path=vm.full_path))


class HighVmCpuUtilization(runbook.Step):
  """Evaluates the CPU of a VM for high utilization that might indicate performance issues.

  This step determines whether the CPU utilization of the VM exceeds a predefined threshold,
  indicating potential performance degradation. It utilizes metrics from the Ops Agent if installed,
  or hypervisor-visible metrics as a fallback, to accurately assess CPU performance and identify any
  issues requiring attention.
  """

  template = 'vm_performance::high_cpu_utilization'

  project_id: Optional[str] = None
  zone: Optional[str] = None
  instance_name: Optional[str] = None
  vm: Optional[gce.Instance] = None

  def execute(self):
    """Verify VM CPU utilization is within optimal levels"""
    if self.vm:
      vm = self.vm
      self.project_id = vm.project_id
      self.zone = vm.zone
      self.instance_name = vm.name
    else:
      vm = gce.get_instance(
          project_id=self.project_id,
          zone=self.zone,
          instance_name=self.instance_name,
      )

    if not vm:
      op.add_skipped(
          None,
          reason=(f'VM instance {self.instance_name} not found in project'
                  f' {self.project_id} zone {self.zone}'),
      )
      return

    start_formatted_string = op.get(
        flags.START_TIME).strftime('%Y/%m/%d %H:%M:%S')
    end_formatted_string = op.get(flags.END_TIME).strftime('%Y/%m/%d %H:%M:%S')
    within_str = (
        f"within d'{start_formatted_string}', d'{end_formatted_string}'")

    cpu_usage_metrics = None

    if util.ops_agent_installed(self.project_id, vm.id):
      cpu_usage_metrics = monitoring.query(
          self.project_id, """
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
          self.project_id, """
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
                    reason=op.prep_msg(op.FAILURE_REASON,
                                       full_resource_path=vm.full_path),
                    remediation=op.prep_msg(op.FAILURE_REMEDIATION,
                                            full_resource_path=vm.full_path))
    else:
      op.add_ok(vm,
                reason=op.prep_msg(op.SUCCESS_REASON,
                                   full_resource_path=vm.full_path))


class VmLifecycleState(runbook.Step):
  """Validates that a specified VM is in the 'RUNNING' state.

  This step is crucial for confirming the VM's availability and operational
  readiness. It checks the VM's lifecycle state and reports success if the VM
  is running or fails the check if the VM is in any other state, providing
  detailed status information for troubleshooting.
  """

  template = 'vm_attributes::running'

  project_id: Optional[str] = None
  zone: Optional[str] = None
  instance_name: Optional[str] = None
  vm: Optional[gce.Instance] = None
  expected_lifecycle_status: str

  def execute(self):
    """Verify GCE Instance is in the {expected_lifecycle_status} state."""
    if self.vm:
      vm = self.vm
    else:
      vm = gce.get_instance(project_id=self.project_id,
                            zone=self.zone,
                            instance_name=self.instance_name)
    if not vm:
      op.add_skipped(
          None,
          reason=(f'VM instance {self.instance_name} not found in project'
                  f' {self.project_id} zone {self.zone}'),
      )
      return

    if vm.status == self.expected_lifecycle_status:
      op.add_ok(vm,
                reason=op.prep_msg(op.SUCCESS_REASON,
                                   full_resource_path=vm.full_path,
                                   status=vm.status))
    else:
      op.add_failed(vm,
                    reason=op.prep_msg(op.FAILURE_REASON,
                                       full_resource_path=vm.full_path,
                                       status=vm.status),
                    remediation=op.prep_msg(op.FAILURE_REMEDIATION,
                                            full_resource_path=vm.full_path,
                                            status=vm.status))


class VmSerialLogsCheck(runbook.Step):
  """Searches for predefined good or bad patterns in the serial logs of a GCE Instance.

  This diagnostic step checks the VM's serial logs for patterns that are indicative of successful
  operations ('GOOD_PATTERN') or potential issues ('BAD_PATTERN'). Based on the presence of these
  patterns, the step categorizes the VM's status as 'OK', 'Failed', or 'Uncertain'.
  """

  project_id: Optional[str] = None
  zone: Optional[str] = None
  instance_name: Optional[str] = None
  vm: Optional[gce.Instance] = None
  serial_console_file = None

  template = 'vm_serial_log::default'

  # Typical logs of a fully booted windows VM
  positive_pattern: List
  positive_pattern_operator = 'OR'
  negative_pattern: List
  negative_pattern_operator = 'OR'

  def execute(self):
    """Analyzing serial logs for predefined patterns."""

    # check for parameter overrides for patterns and template
    if op.get('template'):
      self.template = op.get('template')
    if op.get('positive_patterns'):
      self.positive_pattern = runbook_util.resolve_patterns(
          op.get('positive_patterns'), constants)
    if op.get('negative_patterns'):
      self.negative_pattern = runbook_util.resolve_patterns(
          op.get('negative_patterns'), constants)

    if self.vm:
      vm = self.vm
      self.project_id = vm.project_id
      self.zone = vm.zone
      self.instance_name = vm.name
    else:
      vm = gce.get_instance(
          project_id=self.project_id,
          zone=self.zone,
          instance_name=self.instance_name,
      )

    if not vm:
      op.add_skipped(
          None,
          reason=(f'VM instance {self.instance_name} not found in project'
                  f' {self.project_id} zone {self.zone}'),
      )
      return

    # All kernel failures.
    good_pattern_detected = False
    bad_pattern_detected = False
    serial_log_file_content = []
    instance_serial_logs = None

    if self.serial_console_file:
      for files in self.serial_console_file.split(','):
        with open(files, encoding='utf-8') as file:
          serial_log_file_content = file.readlines()
        serial_log_file_content = serial_log_file_content + serial_log_file_content
    else:
      instance_serial_logs = gce.get_instance_serial_port_output(
          project_id=self.project_id,
          zone=self.zone,
          instance_name=self.instance_name)

    if instance_serial_logs or serial_log_file_content:
      instance_serial_log = instance_serial_logs.contents if \
        instance_serial_logs else serial_log_file_content

      if hasattr(self, 'positive_pattern'):
        good_pattern_detected = util.search_pattern_in_serial_logs(
            patterns=self.positive_pattern,
            contents=instance_serial_log,
            operator=self.positive_pattern_operator)
        op.add_metadata('Positive patterns searched in serial logs',
                        self.positive_pattern)
        if good_pattern_detected:
          op.add_ok(vm,
                    reason=op.prep_msg(
                        op.SUCCESS_REASON,
                        full_resource_path=vm.full_path,
                        start_time=op.get(flags.START_TIME),
                        end_time=op.get(flags.END_TIME),
                    ))
      if hasattr(self, 'negative_pattern'):
        # Check for bad patterns
        bad_pattern_detected = util.search_pattern_in_serial_logs(
            patterns=self.negative_pattern,
            contents=instance_serial_log,
            operator=self.negative_pattern_operator)
        op.add_metadata('Negative patterns searched in serial logs',
                        self.negative_pattern)

        if bad_pattern_detected:
          op.add_failed(vm,
                        reason=op.prep_msg(op.FAILURE_REASON,
                                           start_time=op.get(flags.START_TIME),
                                           end_time=op.get(flags.END_TIME),
                                           full_resource_path=vm.full_path,
                                           instance_name=vm.name),
                        remediation=op.prep_msg(
                            op.FAILURE_REMEDIATION,
                            full_resource_path=vm.full_path,
                            start_time=op.get(flags.START_TIME),
                            end_time=op.get(flags.END_TIME)))

      if hasattr(self, 'positive_pattern') and not hasattr(
          self, 'negative_pattern') and good_pattern_detected is False:
        op.add_uncertain(
            vm,
            reason=op.prep_msg(op.UNCERTAIN_REASON,
                               full_resource_path=vm.full_path,
                               start_time=op.get(flags.START_TIME),
                               end_time=op.get(flags.END_TIME)),
            # uncertain uses the same remediation steps as failed
            remediation=op.prep_msg(op.FAILURE_REMEDIATION,
                                    full_resource_path=vm.full_path,
                                    start_time=op.get(flags.START_TIME),
                                    end_time=op.get(flags.END_TIME)))
      elif hasattr(self, 'negative_pattern') and not hasattr(
          self, 'positive_pattern') and bad_pattern_detected is False:
        op.add_uncertain(
            vm,
            reason=op.prep_msg(op.UNCERTAIN_REASON,
                               full_resource_path=vm.full_path),
            # uncertain uses the same remediation steps as failed
            remediation=op.prep_msg(op.FAILURE_REMEDIATION,
                                    full_resource_path=vm.full_path,
                                    start_time=op.get(flags.START_TIME),
                                    end_time=op.get(flags.END_TIME)))
      elif (hasattr(self, 'positive_pattern') and
            good_pattern_detected is False) and (hasattr(
                self, 'negative_pattern') and bad_pattern_detected is False):
        op.add_uncertain(
            vm,
            reason=op.prep_msg(op.UNCERTAIN_REASON,
                               full_resource_path=vm.full_path,
                               start_time=op.get(flags.START_TIME),
                               end_time=op.get(flags.END_TIME)),
            # uncertain uses the same remediation steps as failed
            remediation=op.prep_msg(op.FAILURE_REMEDIATION,
                                    full_resource_path=vm.full_path,
                                    start_time=op.get(flags.START_TIME),
                                    end_time=op.get(flags.END_TIME)))
    else:
      op.add_skipped(None, reason=op.prep_msg(op.SKIPPED_REASON))


class VmMetadataCheck(runbook.Step):
  """Validates a specific boolean metadata key-value pair on a GCE Instance instance.

  This step checks if the VM's metadata contains a specified key with the expected boolean value,
  facilitating configuration verification and compliance checks."""

  template: str = 'vm_metadata::default'

  project_id: Optional[str] = None
  zone: Optional[str] = None
  instance_name: Optional[str] = None
  vm: Optional[gce.Instance] = None
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
    - True if the actual metadata value matches the expected value, False otherwise.
    """
    # Determine the type of the expected value
    if isinstance(self.expected_value, bool):
      # Convert the string metadata value to a bool for comparison
      return op.BOOL_VALUES.get(str(actual_value).lower(),
                                False) == self.expected_value
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
    """Verify VM metadata value."""
    self.project_id = op.get(flags.PROJECT_ID) or self.project_id
    self.instance_name = op.get(flags.INSTANCE_NAME) or self.instance_name
    self.zone = op.get(flags.ZONE) or self.zone
    metadata_key_str = op.get('metadata_key') or getattr(
        self, 'metadata_key', None)
    expected_value_str = op.get('expected_value') or getattr(
        self, 'expected_value', None)

    if not self.instance_name or not self.zone:
      raise runbook_exceptions.MissingParameterError(
          'instance_name and zone must be provided.')
    if not metadata_key_str:
      raise runbook_exceptions.MissingParameterError(
          "'metadata_key' is required for this step.")
    if expected_value_str is None:
      raise runbook_exceptions.MissingParameterError(
          "'expected_value' is required for this step.")

    if metadata_key_str.startswith('ref:'):
      self.metadata_key = getattr(constants, metadata_key_str[4:])
    else:
      self.metadata_key = metadata_key_str

    try:
      resolved_expected_value = _resolve_expected_value(str(expected_value_str))
      # convert to bool if it looks like one.
      if str(resolved_expected_value).lower() in op.BOOL_VALUES:
        self.expected_value = op.BOOL_VALUES[str(
            resolved_expected_value).lower()]
      else:
        self.expected_value = resolved_expected_value
      self.expected_value_type = type(self.expected_value)
    except ValueError as e:
      raise runbook_exceptions.InvalidParameterError(str(e)) from e

    if self.vm:
      vm = self.vm
    else:
      try:
        vm = gce.get_instance(project_id=self.project_id,
                              zone=self.zone,
                              instance_name=self.instance_name)
      except apiclient.errors.HttpError as err:
        if err.resp.status == 404:
          op.add_skipped(
              None,
              reason=(f'VM instance {self.instance_name} not found in project'
                      f' {self.project_id} zone {self.zone}'),
          )
          return
        else:
          raise utils.GcpApiError(err) from err
    if not vm:
      op.add_skipped(
          None,
          reason=(f'VM instance {self.instance_name} not found in project'
                  f' {self.project_id} zone {self.zone}'),
      )
      return

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
  """Checks if ingress or egress traffic is allowed to a GCE Instance from a specified source IP.

  Evaluates VPC firewall rules to verify if a GCE Instance permits ingress or egress traffic from a
  designated source IP through a specified port and protocol.
  """
  project_id: Optional[str] = None
  zone: Optional[str] = None
  instance_name: Optional[str] = None
  vm: Optional[gce.Instance] = None
  src_ip: str
  protocol_type: str
  port: int

  traffic = None

  def execute(self):
    """Evaluating VPC network traffic rules."""
    if self.vm:
      vm = self.vm
    else:
      vm = gce.get_instance(
          project_id=self.project_id,
          zone=self.zone,
          instance_name=self.instance_name,
      )
    if not vm:
      op.add_skipped(
          None,
          reason=(f'VM instance {self.instance_name} not found in project'
                  f' {self.project_id} zone {self.zone}'),
      )
      return

    result = None
    if self.traffic == 'ingress':
      result = vm.network.firewall.check_connectivity_ingress(
          src_ip=self.src_ip,
          ip_protocol=self.protocol_type,
          port=self.port,
          target_service_account=vm.service_account,
          target_tags=vm.tags)
    if self.traffic == 'egress':
      result = vm.network.firewall.check_connectivity_egress(
          src_ip=vm.network_ips,
          ip_protocol=self.protocol_type,
          port=self.port,
          target_service_account=vm.service_account,
          target_tags=vm.tags)
    if result.action == 'deny':
      op.add_failed(vm,
                    reason=op.prep_msg(op.FAILURE_REASON,
                                       address=self.src_ip,
                                       protocol=self.protocol_type,
                                       port=self.port,
                                       name=vm.name,
                                       result=result.matched_by_str),
                    remediation=op.prep_msg(op.FAILURE_REMEDIATION))
    elif result.action == 'allow':
      op.add_ok(
          vm,
          op.prep_msg(op.SUCCESS_REASON,
                      address=self.src_ip,
                      protocol=self.protocol_type,
                      port=self.port,
                      name=vm.name,
                      result=result.matched_by_str))


class VmScope(runbook.Step):
  """Verifies that a GCE Instance has at least one of a list of required access scopes

  Confirms that the VM has the necessary OAuth scope
  https://cloud.google.com/compute/docs/access/service-accounts#accesscopesiam

  Attributes
   - Use `access_scopes` to specify eligible access scopes
   - Set `require_all` to True if the VM should have all the required access. False (default)
     means to check if it has at least one of the required access scopes
  """

  template = 'vm_attributes::access_scope'
  access_scopes: Set = set()
  require_all = False
  project_id: Optional[str] = None
  zone: Optional[str] = None
  instance_name: Optional[str] = None
  vm: Optional[gce.Instance] = None

  def execute(self):
    """Verify GCE Instance access scope"""
    if self.vm:
      instance = self.vm
    else:
      instance = gce.get_instance(
          project_id=self.project_id,
          zone=self.zone,
          instance_name=self.instance_name,
      )
    if not instance:
      op.add_skipped(
          None,
          reason=(f'VM instance {self.instance_name} not found in project'
                  f' {self.project_id} zone {self.zone}'),
      )
      return

    present_access_scopes = set()
    missing_access_scopes = set()
    has_item = False
    for scope in self.access_scopes:
      if scope in instance.access_scopes:
        has_item = True

      if has_item:
        present_access_scopes.add(scope)
      else:
        missing_access_scopes.add(scope)
      # Reset to false after tracking
      has_item = False

    all_present = not missing_access_scopes
    any_present = bool(present_access_scopes)
    outcome = all_present if self.require_all else any_present

    if outcome:
      op.add_ok(resource=instance,
                reason=op.prep_msg(op.SUCCESS_REASON,
                                   full_resource_path=instance.full_path,
                                   present_access_scopes=', '.join(
                                       sorted(present_access_scopes))))
    else:
      op.add_failed(
          resource=instance,
          reason=op.prep_msg(
              op.FAILURE_REASON,
              full_resource_path=instance.full_path,
              required_access_scope=', '.join(sorted(self.access_scopes)),
              missing_access_scopes=', '.join(sorted(missing_access_scopes))),
          remediation=op.prep_msg(
              op.FAILURE_REMEDIATION,
              full_resource_path=instance.full_path,
              required_access_scope=', '.join(sorted(self.access_scopes)),
              present_access_scopes=', '.join(sorted(present_access_scopes)),
              missing_access_scopes=', '.join(sorted(missing_access_scopes))))


class VmHasOpsAgent(runbook.Step):
  """Verifies that a GCE Instance has at ops agent installed and

  You can check for sub agents for logging and metrics

  Attributes
   - Set `check_logging` to check for logging sub agent. Defaults is True
   - Set `check_metrics` to check for metrics sub agent. Default is True
  """

  template = 'vm_ops::opsagent_installed'
  check_logging: bool = True
  check_metrics: bool = True

  project_id: Optional[str] = None
  zone: Optional[str] = None
  instance_name: Optional[str] = None
  instance_id: Optional[str] = None
  vm: Optional[gce.Instance] = None
  start_time: datetime
  end_time: datetime

  def _has_ops_agent_subagent(self, metric_data):
    """Checks if ops agent logging agent and metric agent is installed"""
    subagents = {
        'metrics_subagent_installed': False,
        'logging_subagent_installed': False
    }
    if not metric_data:
      return {
          'metrics_subagent_installed': False,
          'logging_subagent_installed': False
      }

    for entry in metric_data.values():
      version = get_path(entry, ('labels', 'metric.version'), '')
      if 'google-cloud-ops-agent-metrics' in version:
        subagents['metrics_subagent_installed'] = True
      if 'google-cloud-ops-agent-logging' in version:
        subagents['logging_subagent_installed'] = True

    return subagents

  def execute(self):
    """Verify GCE Instance's has ops agent installed and currently active"""
    if self.vm:
      instance = self.vm
      self.project_id = instance.project_id
      self.zone = instance.zone
      self.instance_name = instance.name
      self.instance_id = instance.id
    else:
      instance = gce.get_instance(
          project_id=self.project_id,
          zone=self.zone,
          instance_name=self.instance_name or self.instance_id,
      )
    if not instance:
      op.add_skipped(
          None,
          reason=(
              f'VM instance {self.instance_name or self.instance_id} not found'
              f' in project {self.project_id} zone {self.zone}'),
      )
      return

    self.end_time = getattr(self, 'end_time', None) or op.get(self.end_time)
    self.start_time = getattr(self, 'start_time', None) or op.get(
        self.start_time)

    if self.check_logging:
      serial_log_entries = logs.realtime_query(
          project_id=self.project_id,
          filter_str='''resource.type="gce_instance"
                          log_name="projects/{}/logs/ops-agent-health"
                          resource.labels.instance_id="{}"
                          "LogPingOpsAgent"'''.format(self.project_id,
                                                      instance.id),
          start_time=self.start_time,
          end_time=self.end_time)
      if serial_log_entries:
        op.add_ok(resource=instance,
                  reason=op.prep_msg(op.SUCCESS_REASON,
                                     full_resource_path=instance.full_path,
                                     subagent='logging'))
      else:
        op.add_failed(resource=instance,
                      reason=op.prep_msg(op.FAILURE_REASON,
                                         full_resource_path=instance.full_path,
                                         subagent='logging'),
                      remediation=op.prep_msg(
                          op.FAILURE_REMEDIATION,
                          full_resource_path=instance.full_path,
                          subagent='logging'))

    if self.check_metrics:
      ops_agent_uptime = monitoring.query(
          self.project_id, """
                fetch gce_instance
                | metric 'agent.googleapis.com/agent/uptime'
                | filter (resource.instance_id == '{}')
                | align rate(1m)
                | every 1m
                | group_by [resource.instance_id, metric.version],
                    [value_uptime_aggregate: aggregate(value.uptime)]
              """.format(instance.id))
      subagents = self._has_ops_agent_subagent(ops_agent_uptime)
      if subagents['metrics_subagent_installed']:
        op.add_ok(resource=instance,
                  reason=op.prep_msg(op.SUCCESS_REASON,
                                     full_resource_path=instance.full_path,
                                     subagent='metrics'))
      else:
        op.add_failed(resource=instance,
                      reason=op.prep_msg(op.FAILURE_REASON,
                                         full_resource_path=instance.full_path,
                                         subagent='metrics'),
                      remediation=op.prep_msg(
                          op.FAILURE_REMEDIATION,
                          full_resource_path=instance.full_path,
                          subagent='metrics'))


class MigAutoscalingPolicyCheck(runbook.Step):
  """Checks MIG autoscaling policy attributes.

  This step performs checks on attributes within a Managed Instance Group (MIG)'s
  autoscaling policy. It requires both 'property_path' and 'expected_value' to be
  specified.

  The MIG can be identified either by providing 'instance_name' and 'zone' (the
  step will find the MIG associated with the instance) or by providing 'mig_name'
  and 'location' (zone or region).

  Parameters:
  - property_path: The nested path of the property to check within the MIG or
    autoscaler resource (e.g., 'autoscalingPolicy.mode'). If the path starts
    with 'autoscalingPolicy', the autoscaler resource is queried.
  - expected_value: The value to compare against. Supports 'ref:' prefix to
    resolve constants from gce/constants.py (e.g., 'ref:AUTOSCALING_MODE_ON').
  - operator: The comparison operator to use. Supported: 'eq' (default), 'ne',
    'lt', 'le', 'gt', 'ge'.
  """

  template = 'mig_autoscaling::policy_check'
  project_id: Optional[str] = None
  location: Optional[str] = None  # zone or region
  mig_name: Optional[str] = None
  instance_name: Optional[str] = None
  zone: Optional[str] = None

  def execute(self):
    """Check MIG Autoscaling Policy."""
    # Get parameters
    self.project_id = op.get(flags.PROJECT_ID) or self.project_id
    self.location = op.get(flags.LOCATION) or self.location
    self.mig_name = op.get(flags.MIG_NAME) or self.mig_name
    self.instance_name = op.get(flags.INSTANCE_NAME) or self.instance_name
    self.zone = op.get(flags.ZONE) or self.zone

    property_path: Optional[str] = op.get('property_path')
    expected_value_str: Optional[str] = op.get('expected_value')
    operator: str = op.get('operator', 'eq')

    try:
      # If instance details are provided, find MIG from instance
      if self.instance_name and self.zone:
        instance = gce.get_instance(self.project_id, self.zone,
                                    self.instance_name)
        if instance.created_by_mig:
          mig = instance.mig
          self.location = mig.zone or mig.region
          if not self.location:
            op.add_skipped(
                instance,
                reason=
                f'Could not determine location for MIG of instance {self.instance_name}.',
            )
            return
        else:
          op.add_skipped(
              instance,
              reason=
              f'Instance {self.instance_name} is not part of any Managed Instance Group.',
          )
          return
      # If MIG details are provided, fetch MIG directly
      elif self.mig_name and self.location:
        if self.location.count('-') == 2:  # zone
          mig = gce.get_instance_group_manager(self.project_id, self.location,
                                               self.mig_name)
        elif self.location.count('-') == 1:  # region
          mig = gce.get_region_instance_group_manager(self.project_id,
                                                      self.location,
                                                      self.mig_name)
        else:
          raise runbook_exceptions.InvalidParameterError(
              f"Cannot determine if location '{self.location}' is a zone or region."
          )
      else:
        raise runbook_exceptions.MissingParameterError(
            'Either instance_name and zone, or mig_name and location must be provided.'
        )
    except apiclient.errors.HttpError as err:
      if err.resp.status == 404:
        resource = self.instance_name or self.mig_name
        op.add_skipped(
            None,
            reason=
            f'Resource {resource} not found in project {self.project_id}.',
        )
        return
      else:
        raise utils.GcpApiError(err) from err
    except AttributeError:
      op.add_skipped(
          None,
          reason=f'Could not determine MIG for instance {self.instance_name}.',
      )
      return

    if not mig:
      op.add_skipped(None, reason='Could not find MIG to analyze.')
      return

    # Generic check if property_path is provided
    if not property_path:
      raise runbook_exceptions.MissingParameterError(
          "'property_path' is required for this step.")
    if expected_value_str is None:
      raise runbook_exceptions.MissingParameterError(
          "'expected_value' is required for this step.")

    try:
      expected_value = _resolve_expected_value(expected_value_str)
    except ValueError as e:
      raise runbook_exceptions.InvalidParameterError(str(e)) from e

    if property_path and property_path.startswith('autoscalingPolicy'):
      try:
        if mig.zone:  # zonal
          autoscaler = gce.get_autoscaler(self.project_id, mig.zone, mig.name)
          actual_value = autoscaler.get(property_path, default=None)
        else:  # regional
          autoscaler = gce.get_region_autoscaler(self.project_id, mig.region,
                                                 mig.name)
          actual_value = autoscaler.get(property_path, default=None)
      except apiclient.errors.HttpError as err:
        if err.resp.status == 404:
          # No autoscaler linked, policy doesn't exist.
          actual_value = None
        else:
          raise utils.GcpApiError(err) from err
    else:
      actual_value = mig.get(property_path, default=None)

    op.add_metadata('mig_name', mig.name)
    op.add_metadata('property_path', property_path)
    op.add_metadata('expected_value', str(expected_value))
    op.add_metadata('operator', operator)
    op.add_metadata('actual_value', str(actual_value))

    if _check_condition(actual_value, expected_value, operator):
      op.add_ok(
          mig,
          reason=op.prep_msg(
              op.SUCCESS_REASON,
              mig_name=mig.name,
              property_path=property_path,
              expected_value=expected_value,
              operator=operator,
              actual_value=actual_value,
          ),
      )
    else:
      op.add_failed(
          mig,
          reason=op.prep_msg(
              op.FAILURE_REASON,
              mig_name=mig.name,
              property_path=property_path,
              expected_value=expected_value,
              operator=operator,
              actual_value=actual_value,
          ),
          remediation=op.prep_msg(op.FAILURE_REMEDIATION, mig_name=mig.name),
      )


class InstancePropertyCheck(runbook.Step):
  """Checks that a Instance property meets a given condition.

  This step fetches a VM instance and checks if a specified property
  meets the condition defined by an expected value and an operator.
  It supports nested properties via getattr and various operators including
  'eq', 'ne', 'lt', 'le', 'gt', 'ge', 'contains', and 'matches'.

  Parameters:
  - property_path: The path of the property to check on the Instance object
    (e.g., 'status', 'boot_disk_licenses').
  - expected_value: The value to compare against. Supports 'ref:' prefix to
    resolve constants from gce/constants.py (e.g., 'ref:RHEL_PATTERN').
  - operator: The comparison operator to use. Supported: 'eq', 'ne',
    'lt', 'le', 'gt', 'ge', 'contains', 'matches'. Default is 'eq'.

  Operator Notes:
  - `contains`: Checks for exact membership in lists (e.g., 'item' in ['item'])
    or substring in strings.
  - `matches`: Treats `expected_value` as a regex and checks if the pattern is
    found in the string or in *any* element of a list. Useful for partial
    matches (e.g., pattern 'sles' matching license 'sles-12-sap').
  """

  template = 'instance_property::default'
  project_id: Optional[str] = None
  instance_name: Optional[str] = None
  zone: Optional[str] = None

  def execute(self):
    """Check VM property."""
    self.project_id = op.get(flags.PROJECT_ID) or self.project_id
    self.instance_name = op.get(flags.INSTANCE_NAME) or self.instance_name
    self.zone = op.get(flags.ZONE) or self.zone

    property_path: Optional[str] = op.get('property_path')
    expected_value_str: Optional[str] = op.get('expected_value')
    operator: str = op.get('operator', 'eq')

    if not self.instance_name or not self.zone:
      raise runbook_exceptions.MissingParameterError(
          'instance_name and zone must be provided.')
    if not property_path:
      raise runbook_exceptions.MissingParameterError(
          "'property_path' is required for this step.")
    if property_path.startswith('ref:'):
      property_path = getattr(constants, property_path[4:])
    if expected_value_str is None:
      raise runbook_exceptions.MissingParameterError(
          "'expected_value' is required for this step.")

    try:
      vm = gce.get_instance(self.project_id, self.zone, self.instance_name)
    except apiclient.errors.HttpError as err:
      if err.resp.status == 404:
        op.add_skipped(
            None,
            reason=(f'VM instance {self.instance_name} not found in project'
                    f' {self.project_id} zone {self.zone}'),
        )
        return
      else:
        raise utils.GcpApiError(err) from err

    try:
      resolved_expected_value = _resolve_expected_value(expected_value_str)
      if str(resolved_expected_value).lower() in op.BOOL_VALUES:
        expected_value = op.BOOL_VALUES[str(resolved_expected_value).lower()]
      else:
        expected_value = resolved_expected_value
    except ValueError as e:
      raise ValueError(str(e)) from e

    try:
      actual_value = getattr(vm, property_path)
    except (AttributeError, KeyError) as e:
      raise ValueError(
          f"Could not access property_path '{property_path}' on VM instance {self.instance_name}"
      ) from e

    op.add_metadata('instance_name', vm.name)
    op.add_metadata('property_path', property_path)
    op.add_metadata('expected_value', str(expected_value))
    op.add_metadata('operator', operator)
    op.add_metadata('actual_value', str(actual_value))

    if _check_condition(actual_value, expected_value, operator):
      op.add_ok(
          vm,
          reason=op.prep_msg(
              op.SUCCESS_REASON,
              instance_name=vm.name,
              property_path=property_path,
              expected_value=expected_value,
              operator=operator,
              actual_value=actual_value,
          ),
      )
    else:
      op.add_failed(
          vm,
          reason=op.prep_msg(
              op.FAILURE_REASON,
              instance_name=vm.name,
              property_path=property_path,
              expected_value=expected_value,
              operator=operator,
              actual_value=actual_value,
          ),
          remediation=op.prep_msg(
              op.FAILURE_REMEDIATION,
              instance_name=vm.name,
              property_path=property_path,
              expected_value=expected_value,
              operator=operator,
          ),
      )


class GceLogCheck(runbook.Step):
  """Executes a Cloud Logging query and checks results against optional patterns.

  This step queries Cloud Logging using the provided filter string by calling
  logs.generalized_steps.CheckIssueLogEntry.
  See CheckIssueLogEntry for logic on FAILED/UNCERTAIN status.

  Parameters retrieved via `op.get()`:
    project_id(str): Project ID to search for filter.
    filter_str(str): Filter in Cloud Logging query language:
      https://cloud.google.com/logging/docs/view/query-library.
    issue_pattern(Optional[str]): Semicolon-separated ';;' list of regex
      patterns to search for in `protoPayload.status.message`. If prefixed
      with 'ref:', it resolves to a list in `gce/constants.py`.
      If provided, logs matching pattern will result in FAILED status.
    resource_name(Optional[str]): Resource identifier for template messages.
    template(Optional[str]): Template name, defaults to
      'logging::gce_log'.
  """

  def execute(self):
    """Check for log entries by calling CheckIssueLogEntry."""
    project_id = op.get(flags.PROJECT_ID)
    filter_str = op.get('filter_str')
    issue_pattern_str = op.get('issue_pattern')
    resource_name = op.get('resource_name', 'resource NA')
    template = op.get('template') or 'logging::gce_log'

    if not project_id:
      raise runbook_exceptions.MissingParameterError(
          "'project_id' is required for this step.")
    if not filter_str:
      raise runbook_exceptions.MissingParameterError(
          "'filter_str' is required for this step.")

    # Resolve filter_str if it is a reference
    if filter_str.startswith('ref:'):
      const_name = filter_str[4:]
      resolved_filter = getattr(constants, const_name, None)
      if resolved_filter is None:
        raise runbook_exceptions.InvalidParameterError(
            f"Could not resolve constant reference: '{filter_str}'. "
            f"Ensure '{const_name}' is defined in gce/constants.py.")
      filter_str = resolved_filter

    issue_patterns = []
    if issue_pattern_str:
      issue_patterns = runbook_util.resolve_patterns(issue_pattern_str,
                                                     constants)

    log_check_step = logs_gs.CheckIssueLogEntry(project_id=project_id,
                                                filter_str=filter_str,
                                                issue_pattern=issue_patterns,
                                                template=template,
                                                resource_name=resource_name)
    self.add_child(log_check_step)


class GceIamPolicyCheck(runbook.Step):
  """Checks IAM policies by calling IamPolicyCheck with support for gce/constants.py.

  This step is a wrapper around iam.generalized_steps.IamPolicyCheck that adds
  support for resolving 'roles' or 'permissions' parameters from gce/constants.py
  if they are prefixed with 'ref:'. It also supports ';;' delimited strings for
  roles or permissions lists.

  Parameters retrieved via `op.get()`:
    project_id(str): Project ID to check policy against.
    principal(str): The principal to check (e.g., user:x@y.com,
      serviceAccount:a@b.com).
    roles(Optional[str]): ';;' separated list of roles or 'ref:CONSTANT' to check.
    permissions(Optional[str]): ';;' separated list of permissions or
      'ref:CONSTANT' to check.
    require_all(bool): If True, all roles/permissions must be present.
      If False (default), at least one must be present.
  """

  def execute(self):
    """Check IAM policies by calling IamPolicyCheck."""
    project_id = op.get(flags.PROJECT_ID)
    principal = op.get(iam_flags.PRINCIPAL)
    roles_str = op.get('roles')
    permissions_str = op.get('permissions')
    require_all = op.BOOL_VALUES.get(
        str(op.get('require_all', False)).lower(), False)

    if not project_id:
      raise runbook_exceptions.MissingParameterError(
          "'project_id' is required for this step.")
    if not principal:
      raise runbook_exceptions.MissingParameterError(
          "'principal' is required for this step.")
    if not roles_str and not permissions_str:
      raise runbook_exceptions.MissingParameterError(
          "Either 'roles' or 'permissions' must be provided.")

    roles_set = None
    if roles_str:
      roles_set = set(runbook_util.resolve_patterns(roles_str, constants))

    permissions_set = None
    if permissions_str:
      permissions_set = set(
          runbook_util.resolve_patterns(permissions_str, constants))

    iam_check_step = iam_gs.IamPolicyCheck(project=project_id,
                                           principal=principal,
                                           roles=roles_set,
                                           permissions=permissions_set,
                                           require_all=require_all)
    self.add_child(iam_check_step)
