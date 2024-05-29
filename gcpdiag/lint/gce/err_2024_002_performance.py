# Copyright 2024 Google LLC
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
""" GCE VM is operating within optimal performance thresholds

Checks the performance of the GCE instances in a project -
CPU Usage, Memory Usage, Disk Usage and Serial port logs errors.
Threshold for CPU Usage, Memory Usage, Disk Usage is 95%.
"""

import operator as op

from gcpdiag import lint, models
from gcpdiag.lint.gce import utils
from gcpdiag.queries import gce, monitoring

vm = None
project = None
within_hours = 9
within_str = 'within %dh, d\'%s\'' % (within_hours,
                                      monitoring.period_aligned_now(5))

UTILIZATION_THRESHOLD = 0.95
IO_LATENCY_THRESHOLD = 1500

mem_search = None
disk_search = None
instances = []


def prepare_rule(context: models.Context):

  vm_oom_pattern = [
      'Out of memory: Kill process', 'Kill process',
      'Memory cgroup out of memory'
  ]

  filter_oom_str = '''textPayload:("oom" OR "Out of memory")
  AND ("Out of memory: Kill" OR "invoked oom-killer" OR "Memory cgroup out of memory")'''

  vm_disk_space_error_pattern = [
      'No space left on device', 'No usable temporary directory found in',
      'A stop job is running for Security ...', 'disk is at or near capacity'
  ]

  filter_disk_str = '''textPayload:("No space left" OR "No usable temporary directory")
  AND ("No space left on device" OR "No usable temporary directory found in"
  OR "disk is at or near capacity"
  OR "A stop job is running for Security ...ing Service ")
  OR "A stop job is running for Security ...ng Service ")
  OR "A stop job is running for Security ...diting Service ")
  OR "A stop job is running for Security ...Auditing Service ")'''

  global mem_search
  mem_search = utils.SerialOutputSearch(context,
                                        search_strings=vm_oom_pattern,
                                        custom_filter=filter_oom_str)

  global disk_search
  disk_search = utils.SerialOutputSearch(
      context,
      search_strings=vm_disk_space_error_pattern,
      custom_filter=filter_disk_str)

  # Fetching the list of instances in the project
  global instances
  instances = [
      vm for vm in gce.get_instances(context).values() if not vm.is_gke_node()
  ]


def run_rule(context: models.Context, report: lint.LintReportRuleInterface):
  """Checking VM performance"""

  if not instances:
    report.add_skipped(None, 'no instances found')
    return

  for i in sorted(instances, key=op.attrgetter('project_id', 'name')):
    if not i.is_running:
      report.add_skipped(i, reason=f'VM {i.name} is in {i.status} state')
    else:
      disk_usage = None
      mem_usage = None
      cpu_usage = None
      ops_agent_installed = None
      ops_agent_installed = monitoring.query(
          context.project_id, """
                fetch gce_instance
                | metric 'agent.googleapis.com/agent/uptime'
                | filter (resource.instance_id == '{}')
                | align rate(5m)
                | every 5m
                | {}
              """.format(i.name, within_str))

      if ops_agent_installed:
        cpu_usage = monitoring.query(
            context.project_id, """
          fetch gce_instance
            | metric 'agent.googleapis.com/cpu/utilization'
            | filter (resource.instance_id == '{}') && (metric.cpu_state != 'idle')
            | group_by [resource.instance_id], 30m, [value_utilization_mean: mean(value.utilization)]
            | filter (cast_units(value_utilization_mean,"")/100) >= {}
            | {}
          """.format(i.id, UTILIZATION_THRESHOLD, within_str))

        mem_usage = monitoring.query(
            context.project_id, """
          fetch gce_instance
            | metric 'agent.googleapis.com/memory/percent_used'
            | filter (resource.instance_id == '{}')
            | group_by [resource.instance_id], 30m, [percent_used: mean(value.percent_used)]
            | filter (cast_units(percent_used,"")/100) >= {}
            | {}
          """.format(i.id, UTILIZATION_THRESHOLD, within_str))

        disk_usage = monitoring.query(
            context.project_id, """
          fetch gce_instance
            | metric 'agent.googleapis.com/disk/percent_used'
            | filter (resource.instance_id == '{}')
            | filter (metric.device !~ '/dev/loop.*' && metric.state == 'used')
            | group_by [resource.instance_id], 30m, [percent_used: max(value.percent_used)]
            | group_by [], [value_percent_used_max: max(percent_used)]
            | filter (cast_units(value_percent_used_max,"")/100) >= {}
            | {}
          """.format(i.id, UTILIZATION_THRESHOLD, within_str))

      else:
        cpu_usage = monitoring.query(
            context.project_id, """
          fetch gce_instance
            | metric 'compute.googleapis.com/instance/cpu/utilization'
            | filter (resource.instance_id == '{}')
            | group_by 30m, [value_utilization_max: mean(value.utilization)]
            | filter value_utilization_max >= {}
            | {}
          """.format(i.id, UTILIZATION_THRESHOLD, within_str))

        if 'e2' in i.machine_type():
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
              """.format(i.id, UTILIZATION_THRESHOLD, within_str))

      # fallback on serial logs to see if there are any OOM logs, defined as vm_oom_pattern
      mem_errors = None
      if mem_search:
        mem_errors = mem_search.get_last_match(i.id)

      # fallback on serial logs to see if there are any Disk related errors/events,
      # defined as vm_disk_space_error_pattern
      disk_errors = None
      if disk_search:
        disk_errors = disk_search.get_last_match(i.id)

      # Checking Disk IO latency for the instance -
      disk_io_latency = monitoring.query(
          context.project_id, """
        fetch gce_instance
        | metric 'compute.googleapis.com/instance/disk/average_io_latency'
        | filter (resource.instance_id == '{}')
        | group_by 1m, [value_average_io_latency_mean: mean(value.average_io_latency)]
        | every 1m
        | group_by [metric.device_name], [value_average_io_latency_mean_percentile: percentile(value_average_io_latency_mean, 99)]
        | filter(cast_units(value_average_io_latency_mean_percentile,"")/1000) >= {}
        | {}
        """.format(i.name, IO_LATENCY_THRESHOLD, within_str))

      if cpu_usage:
        report.add_failed(
            i, ('CPU utilization is exceeding optimal levels, potentially '
                'impacting performance of the instance.'))
      else:
        report.add_ok(i, 'CPU utilization is under optimal levels')

      if mem_usage:
        report.add_failed(
            i,
            ('Memory utilization is exceeding optimal levels(95%), potentially '
             'impacting performance of the instance.'))
      elif mem_errors:
        # fallback on serial logs to see if there are any OOM logs, defined as vm_oom_pattern
        report.add_failed(
            i, ('Found OOM related events in Serial console logs, potentially '
                'impacting performance of the instance.'))
      else:
        report.add_ok(i, 'Memory utilization is under optimal levels')

      if disk_usage:
        report.add_failed(
            i,
            ('Disk utilization is exceeding optimal levels(95%), potentially '
             'impacting performance of the instance.'))
      elif disk_errors:
        report.add_failed(
            i, ('Found Disk related errors/events in Serial console logs, '
                'could be causing issue with instance'))
      else:
        report.add_ok(i, 'Disk utilization is under optimal levels')

      if disk_io_latency:
        report.add_failed(
            i, ('Disk IO Latency is exceeding optimal levels, potentially '
                'impacting performance of the instance.'))
      else:
        report.add_ok(i, 'Disk IO Latency is under optimal levels')
