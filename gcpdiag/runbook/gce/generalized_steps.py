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
from gcpdiag.queries import gce, iam, logs, monitoring
from gcpdiag.runbook import op
from gcpdiag.runbook.gce import constants, flags, util

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
      if 'e2' not in vm.machine_type():
        # Checking for OOM related errors
        oom_errors = VmSerialLogsCheck()
        oom_errors.template = 'vm_performance::high_memory_utilization'
        oom_errors.negative_pattern = constants.OOM_PATTERNS
        self.add_child(oom_errors)

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
            | filter (resource.instance_id == '{}' && metric.device !~ '/dev/loop.*' && metric.state == 'used')
            | group_by [resource.instance_id], 3m, [percent_used: mean(value.percent_used)]
            | filter (cast_units(percent_used,"")/100) >= {}
            | {}
          """.format(vm.id, UTILIZATION_THRESHOLD, within_str))
    else:
      # Fallback to heck for fs utilization related messages in Serial logs
      fs_util = VmSerialLogsCheck()
      fs_util.template = 'vm_performance::high_disk_utilization'
      fs_util.negative_pattern = constants.DISK_EXHAUSTION_ERRORS
      fs_util.uncertain_remediation = False
      self.add_child(fs_util)

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
  positive_pattern: List
  positive_pattern_operator = 'OR'
  negative_pattern: List
  negative_pattern_operator = 'OR'

  def execute(self):
    """Analyzing serial logs for predefined patterns..."""
    # All kernel failures.
    good_pattern_detected = False
    bad_pattern_detected = False
    serial_log_file_content = []
    instance_serial_logs = None
    vm = gce.get_instance(project_id=op.get(flags.PROJECT_ID),
                          zone=op.get(flags.ZONE),
                          instance_name=op.get(flags.NAME))

    if op.get(flags.SERIAL_CONSOLE_FILE):
      for files in op.get(flags.SERIAL_CONSOLE_FILE).split(','):
        with open(files, encoding='utf-8') as file:
          serial_log_file_content = file.readlines()
        serial_log_file_content = serial_log_file_content + serial_log_file_content
    else:
      instance_serial_logs = gce.get_instance_serial_port_output(
          project_id=op.get(flags.PROJECT_ID),
          zone=op.get(flags.ZONE),
          instance_name=op.get(flags.NAME))

    if instance_serial_logs or serial_log_file_content:
      instance_serial_log = instance_serial_logs.contents if \
        instance_serial_logs else serial_log_file_content

      if hasattr(self, 'positive_pattern'):
        good_pattern_detected = util.search_pattern_in_serial_logs(
            patterns=self.positive_pattern,
            contents=instance_serial_log,
            operator=self.positive_pattern_operator)
        if good_pattern_detected:
          op.add_ok(vm,
                    reason=op.prep_msg(op.SUCCESS_REASON,
                                       instance_name=vm.name))
      if hasattr(self, 'negative_pattern'):
        # Check for bad patterns
        bad_pattern_detected = util.search_pattern_in_serial_logs(
            patterns=self.negative_pattern,
            contents=instance_serial_log,
            operator=self.negative_pattern_operator)
        if bad_pattern_detected:
          op.add_failed(vm,
                        reason=op.prep_msg(op.FAILURE_REASON,
                                           instance_name=vm.name),
                        remediation=op.prep_msg(op.FAILURE_REMEDIATION))
      if not good_pattern_detected and not bad_pattern_detected:
        op.add_uncertain(vm,
                         reason=op.prep_msg(op.UNCERTAIN_REASON),
                         remediation=op.prep_msg(op.UNCERTAIN_REMEDIATION))
    else:
      op.add_skipped(vm,
                     reason=op.prep_msg(op.SKIPPED_REASON,
                                        instance_name=vm.name))


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


class VmScope(runbook.Step):
  """Verifies that a GCE VM has at least one of a list of required access scopes

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

  def execute(self):
    """Verifying GCE VM access scope"""
    instance = gce.get_instance(project_id=op.get(flags.PROJECT_ID),
                                zone=op.get(flags.ZONE),
                                instance_name=op.get(flags.NAME))
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
                                   vm_name=instance.name,
                                   present_access_scopes=', '.join(
                                       sorted(present_access_scopes))))
    else:
      op.add_failed(
          resource=instance,
          reason=op.prep_msg(
              op.FAILURE_REASON,
              vm_name=instance.name,
              required_access_scope=', '.join(sorted(self.access_scopes)),
              missing_access_scopes=', '.join(sorted(missing_access_scopes))),
          remediation=op.prep_msg(
              op.FAILURE_REMEDIATION,
              vm_name=instance.name,
              required_access_scope=', '.join(sorted(self.access_scopes)),
              present_access_scopes=', '.join(sorted(present_access_scopes)),
              missing_access_scopes=', '.join(sorted(missing_access_scopes))))


class VmHasOpsAgent(runbook.Step):
  """Verifies that a GCE VM has at ops agent installed and

  You can check for sub agents for logging and metrics

  Attributes
   - Set `check_logging` to check for logging sub agent. Defaults is True
   - Set `check_metrics` to check for metrics sub agent. Default is True
  """

  template = 'vm_ops::opsagent_installed'
  check_logging: bool = True
  check_metrics: bool = True
  start_time_utc: datetime
  end_time_utc: datetime

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
    """Verifying GCE VM's has ops agent installed and currently active"""
    self.end_time_utc = getattr(self, 'end_time_utc', None) or op.get(
        flags.END_TIME_UTC)
    self.start_time_utc = getattr(self, 'start_time_utc', None) or op.get(
        flags.START_TIME_UTC)
    instance = gce.get_instance(project_id=op.get(flags.PROJECT_ID),
                                zone=op.get(flags.ZONE),
                                instance_name=op.get(flags.NAME) or
                                op.get(flags.ID))
    if self.check_logging:
      serial_log_entries = logs.realtime_query(
          project_id=op.get(flags.PROJECT_ID),
          filter_str='''resource.type="gce_instance"
                          log_name="projects/{}/logs/ops-agent-health"
                          resource.labels.instance_id="{}"
                          "LogPingOpsAgent"'''.format(op.get(flags.PROJECT_ID),
                                                      op.get(flags.ID)),
          start_time_utc=self.start_time_utc,
          end_time_utc=self.end_time_utc)
      if serial_log_entries:
        op.add_ok(resource=instance,
                  reason=op.prep_msg(op.SUCCESS_REASON,
                                     vm_name=instance.name,
                                     subagent='logging'))
      else:
        op.add_failed(resource=instance,
                      reason=op.prep_msg(op.FAILURE_REASON,
                                         vm_name=instance.name,
                                         subagent='logging'),
                      remediation=op.prep_msg(op.FAILURE_REMEDIATION,
                                              vm_name=instance.name,
                                              subagent='logging'))

    if self.check_metrics:
      ops_agent_uptime = monitoring.query(
          op.get(flags.PROJECT_ID), """
                fetch gce_instance
                | metric 'agent.googleapis.com/agent/uptime'
                | filter (resource.instance_id == '{}')
                | align rate(1m)
                | every 1m
                | group_by [resource.instance_id, metric.version],
                    [value_uptime_aggregate: aggregate(value.uptime)]
              """.format(op.get(flags.ID)))
      subagents = self._has_ops_agent_subagent(ops_agent_uptime)
      if subagents['metrics_subagent_installed']:
        op.add_ok(resource=instance,
                  reason=op.prep_msg(op.SUCCESS_REASON,
                                     vm_name=instance.name,
                                     subagent='metrics'))
      else:
        op.add_failed(resource=instance,
                      reason=op.prep_msg(op.FAILURE_REASON,
                                         vm_name=instance.name,
                                         subagent='metrics'),
                      remediation=op.prep_msg(op.FAILURE_REMEDIATION,
                                              vm_name=instance.name,
                                              subagent='metrics'))
