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
from datetime import datetime
from typing import Any, List, Set

from boltons.iterutils import get_path

from gcpdiag import runbook
from gcpdiag.queries import gce, logs, monitoring
from gcpdiag.runbook import op
from gcpdiag.runbook.gce import constants, flags, util

UTILIZATION_THRESHOLD = 0.95


class HighVmMemoryUtilization(runbook.Step):
  """Diagnoses high memory utilization issues in a Compute Engine VM.

  This step evaluates memory usage through available monitoring data or, as a fallback, scans serial
  logs for Out of Memory (OOM) indicators. It distinguishes between VMs which has exported metrics
  and those without, and employs a different strategy for 'e2' machine types to accurately assess
  memory utilization.
  """
  template = 'vm_performance::high_memory_utilization'

  project_id: str
  zone: str
  instance_name: str
  serial_console_file = None

  # Typcial Memory exhaustion logs in serial console.

  def execute(self):
    """Verify VM memory utilization is within optimal levels."""

    start_formatted_string = op.get(
        flags.START_TIME).strftime('%Y/%m/%d %H:%M:%S')
    end_formatted_string = op.get(flags.END_TIME).strftime('%Y/%m/%d %H:%M:%S')
    within_str = f'within d\'{start_formatted_string}\', d\'{end_formatted_string}\''

    mark_no_ops_agent = False

    vm = gce.get_instance(
        project_id=self.project_id,
        zone=self.zone,
        instance_name=self.instance_name,
    )

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
    oom_errors.project_id = self.project_id
    oom_errors.zone = self.zone
    oom_errors.instance_name = self.instance_name
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

  project_id: str
  zone: str
  instance_name: str
  serial_console_file: str = ''

  def execute(self):
    """Verify VM's Boot disk space utilization is within optimal levels."""

    start_formatted_string = op.get(
        flags.START_TIME).strftime('%Y/%m/%d %H:%M:%S')
    end_formatted_string = op.get(flags.END_TIME).strftime('%Y/%m/%d %H:%M:%S')
    within_str = f'within d\'{start_formatted_string}\', d\'{end_formatted_string}\''

    mark_no_ops_agent = False

    vm = gce.get_instance(
        project_id=self.project_id,
        zone=self.zone,
        instance_name=self.instance_name,
    )

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
      fs_util.project_id = self.project_id
      fs_util.zone = self.zone
      fs_util.instance_name = self.instance_name
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

  project_id: str
  zone: str
  instance_name: str

  def execute(self):
    """Verify VM CPU utilization is within optimal levels"""

    start_formatted_string = op.get(
        flags.START_TIME).strftime('%Y/%m/%d %H:%M:%S')
    end_formatted_string = op.get(flags.END_TIME).strftime('%Y/%m/%d %H:%M:%S')
    within_str = f'within d\'{start_formatted_string}\', d\'{end_formatted_string}\''

    vm = gce.get_instance(
        project_id=self.project_id,
        zone=self.zone,
        instance_name=self.instance_name,
    )
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

  This step is crucial for confirming the VM's availability and operational readiness.
  It checks the VM's lifecycle state and reports success if the VM is running or fails the
  check if the VM is in any other state, providing detailed status information for
  troubleshooting.
  """

  template = 'vm_attributes::running'

  project_id: str
  zone: str
  instance_name: str
  expected_lifecycle_status: str

  def execute(self):
    """Verify GCE Instance is in the {expected_lifecycle_status} state."""
    vm = gce.get_instance(project_id=self.project_id,
                          zone=self.zone,
                          instance_name=self.instance_name)
    if not vm:
      op.add_skipped(None, reason=op.prep_msg(op.SKIPPED_REASON))
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

  project_id: str
  zone: str
  instance_name: str
  serial_console_file = None

  template = 'vm_serial_log::default'

  # Typical logs of a fully booted windows VM
  positive_pattern: List
  positive_pattern_operator = 'OR'
  negative_pattern: List
  negative_pattern_operator = 'OR'

  def execute(self):
    """Analyzing serial logs for predefined patterns."""
    # All kernel failures.
    good_pattern_detected = False
    bad_pattern_detected = False
    serial_log_file_content = []
    instance_serial_logs = None
    vm = gce.get_instance(
        project_id=self.project_id,
        zone=self.zone,
        instance_name=self.instance_name,
    )

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
            # uncetain uses the same remediation steps as failed
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
            # uncetain uses the same remediation steps as failed
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
            # uncetain uses the same remediation steps as failed
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

  project_id: str
  zone: str
  instance_name: str
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
    vm = gce.get_instance(project_id=self.project_id,
                          zone=self.zone,
                          instance_name=self.instance_name)

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
  project_id: str
  zone: str
  instance_name: str
  src_ip: str
  protocol_type: str
  port: int

  traffic = None

  def execute(self):
    """Evaluating VPC network traffic rules."""
    vm = gce.get_instance(project_id=self.project_id,
                          zone=self.zone,
                          instance_name=self.instance_name)
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
  project_id: str
  zone: str
  instance_name: str

  def execute(self):
    """Verify GCE Instance access scope"""
    instance = gce.get_instance(project_id=self.project_id,
                                zone=self.zone,
                                instance_name=self.instance_name)
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

  project_id: str
  zone: str
  instance_name: str
  instance_id: str
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
    self.end_time = getattr(self, 'end_time', None) or op.get(self.end_time)
    self.start_time = getattr(self, 'start_time', None) or op.get(
        self.start_time)
    instance = gce.get_instance(project_id=self.project_id,
                                zone=self.zone,
                                instance_name=self.instance_name or
                                self.instance_id)
    if self.check_logging:
      serial_log_entries = logs.realtime_query(
          project_id=self.project_id,
          filter_str='''resource.type="gce_instance"
                          log_name="projects/{}/logs/ops-agent-health"
                          resource.labels.instance_id="{}"
                          "LogPingOpsAgent"'''.format(self.project_id,
                                                      self.instance_id),
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
              """.format(self.instance_id))
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
