# Copyright 2024 Google LLC
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
"""Module containing VM performance diagnostic tree and custom steps"""

import json
from datetime import datetime, timedelta, timezone
from os.path import dirname

import googleapiclient.errors

from gcpdiag import config, runbook
from gcpdiag.queries import crm, gce, logs, monitoring
from gcpdiag.runbook import op
from gcpdiag.runbook.gce import constants as gce_const
from gcpdiag.runbook.gce import flags
from gcpdiag.runbook.gce import generalized_steps as gce_gs

IO_LATENCY_THRESHOLD = 1500


class VmPerformance(runbook.DiagnosticTree):
  """ Google Compute Engine VM performance checks

  This runbook is designed to assist you in investigating and understanding the underlying reasons
  behind the performance issues of your Google Compute Engine VMs within Google Cloud Platform.

  Key Investigation Areas:

    - High CPU utilisation
    - CPU Over-commitment for E2 or Sole-Tenant VMs
    - High Memory utilisation
    - Disk space high utilisation
    - High Disk IOPS utilisation
    - High Disk Throughput utilisation
    - Disk Health check
    - Disk IO latency check
    - Disk Slowness check
    - Check for Live Migrations
    - Usual Error checks in Serial console logs
  """

  # Specify parameters common to all steps in the diagnostic tree class.
  parameters = {
      flags.PROJECT_ID: {
          'type': str,
          'help': (
              'The Project ID associated with the VM having performance issues.'
          ),
          'required': True
      },
      flags.NAME: {
          'type':
              str,
          'help':
              'The name of the VM having performance issues. Or provide the id i.e -p name=<int>',
          'required':
              True
      },
      flags.ZONE: {
          'type':
              str,
          'help':
              'The Google Cloud zone where the VM having performance issues, is located.',
          'required':
              True
      },
      flags.START_TIME: {
          'type': datetime,
          'help':
              'The start window(in UTC) to investigate vm performance issues.'
              'Format: YYYY-MM-DDTHH:MM:SSZ'
      },
      flags.END_TIME: {
          'type':
              datetime,
          'help':
              'The end window(in UTC) for the investigation. Format: YYYY-MM-DDTHH:MM:SSZ'
      }
  }

  def build_tree(self):
    """Construct the diagnostic tree with appropriate steps."""

    start = VmPerformanceStart()
    cpu_check = gce_gs.HighVmCpuUtilization()
    cpu_check.project_id = op.get(flags.PROJECT_ID)
    cpu_check.zone = op.get(flags.ZONE)
    cpu_check.instance_name = op.get(flags.NAME)
    mem_check = gce_gs.HighVmMemoryUtilization()
    mem_check.project_id = op.get(flags.PROJECT_ID)
    mem_check.zone = op.get(flags.ZONE)
    mem_check.instance_name = op.get(flags.NAME)
    disk_util_check = gce_gs.HighVmDiskUtilization()
    disk_util_check.project_id = op.get(flags.PROJECT_ID)
    disk_util_check.zone = op.get(flags.ZONE)
    disk_util_check.instance_name = op.get(flags.NAME)

    vm_lifecycle_check = gce_gs.VmLifecycleState()
    vm_lifecycle_check.expected_lifecycle_status = 'RUNNING'
    vm_lifecycle_check.project_id = op.get(flags.PROJECT_ID)
    vm_lifecycle_check.zone = op.get(flags.ZONE)
    vm_lifecycle_check.instance_name = op.get(flags.NAME)

    self.add_start(step=start)
    self.add_step(parent=start, child=vm_lifecycle_check)
    self.add_step(parent=start, child=cpu_check)
    self.add_step(parent=start, child=mem_check)
    self.add_step(parent=cpu_check, child=CpuOvercommitmentCheck())
    self.add_step(parent=start, child=DiskHealthCheck())
    self.add_step(parent=start, child=disk_util_check)
    self.add_step(parent=start, child=DiskAvgIOLatencyCheck())

    # Check for PD slow Reads/Writes
    slow_disk_io = gce_gs.VmSerialLogsCheck()
    slow_disk_io.project_id = op.get(flags.PROJECT_ID)
    slow_disk_io.zone = op.get(flags.ZONE)
    slow_disk_io.instance_name = op.get(flags.NAME)
    slow_disk_io.template = 'vm_performance::slow_disk_io'
    slow_disk_io.negative_pattern = gce_const.SLOW_DISK_READS
    self.add_step(parent=disk_util_check, child=slow_disk_io)

    # Checking for Filesystem corruption related errors
    fs_corruption = gce_gs.VmSerialLogsCheck()
    fs_corruption.project_id = op.get(flags.PROJECT_ID)
    fs_corruption.zone = op.get(flags.ZONE)
    fs_corruption.instance_name = op.get(flags.NAME)
    fs_corruption.template = 'vm_serial_log::linux_fs_corruption'
    fs_corruption.negative_pattern = gce_const.FS_CORRUPTION_MSG
    self.add_step(parent=disk_util_check, child=fs_corruption)

    self.add_step(parent=start, child=CheckLiveMigrations())

    self.add_end(step=VmPerformanceEnd())


class VmPerformanceStart(runbook.StartStep):
  """Fetching VM details."""

  template = 'vm_attributes::running'

  def execute(self):
    """Fetching VM details"""

    project = crm.get_project(op.get(flags.PROJECT_ID))
    try:
      vm = gce.get_instance(project_id=op.get(flags.PROJECT_ID),
                            zone=op.get(flags.ZONE),
                            instance_name=op.get(flags.NAME))
    except googleapiclient.errors.HttpError:
      op.add_skipped(
          project,
          reason=('Instance {} does not exist in zone {} or project {}').format(
              op.get(flags.NAME), op.get(flags.ZONE), op.get(flags.PROJECT_ID)))
    else:
      if vm and vm.is_running:
        # Check for instance id and instance name
        if not op.get(flags.ID):
          op.put(flags.ID, vm.id)
        elif not op.get(flags.NAME):
          op.put(flags.NAME, vm.name)
      else:
        op.add_failed(vm,
                      reason=op.prep_msg(op.FAILURE_REASON,
                                         full_resource_path=vm.full_path,
                                         status=vm.status),
                      remediation=op.prep_msg(op.FAILURE_REMEDIATION,
                                              full_resource_path=vm.full_path,
                                              status=vm.status))


class CheckLiveMigrations(runbook.Step):
  """Checking if live migrations happened for the instance"""

  template = 'vm_performance::live_migrations'

  def execute(self):
    """Checking if live migrations happened for the instance"""

    vm = gce.get_instance(project_id=op.get(flags.PROJECT_ID),
                          zone=op.get(flags.ZONE),
                          instance_name=op.get(flags.NAME))

    logging_filter = '''protoPayload.methodName=~"compute.instances.migrateOnHostMaintenance"'''
    log_entries = logs.realtime_query(
        project_id=op.get(flags.PROJECT_ID),
        filter_str=f'{logging_filter}\nresource.labels.instance_id="{vm.id}"',
        start_time_utc=op.get(flags.START_TIME),
        end_time_utc=op.get(flags.END_TIME))

    time_frame_list = [op.get(flags.START_TIME).strftime('%Y/%m/%d %H:%M:%S')]
    if log_entries:
      for log in log_entries:
        start_time_val = datetime.strptime(
            log['timestamp'],
            '%Y-%m-%dT%H:%M:%S.%fZ').strftime('%Y/%m/%d %H:%M:%S')
        time_frame_list.append(start_time_val)
        op.info(('\n\nLive Migration Detected at {}, Checking further\n\n'
                ).format(start_time_val))
      end_time = op.get(flags.END_TIME).strftime('%Y/%m/%d %H:%M:%S')
      time_frame_list.append(end_time)
      i = 0
      for times in time_frame_list:
        if i < (len(time_frame_list) - 1):
          io_util = DiskIopsThroughputUtilisationChecks()
          i += 1
          io_util.start_time = times
          io_util.end_time = time_frame_list[i]
          self.add_child(io_util)

        #if op.step_failed(io_util.run_id):
        #    op.add_failed(vm,
        #                  reason=op.prep_msg(op.FAILURE_REASON),
        #                  remediation=op.prep_msg(op.FAILURE_REMEDIATION))
    else:
      op.add_ok(vm, reason=op.prep_msg(op.SUCCESS_REASON))
      self.add_child(DiskIopsThroughputUtilisationChecks())


class DiskHealthCheck(runbook.Step):
  """Disk Health check"""

  template = 'vm_performance::disk_health_check'

  def execute(self):
    """Checking if instance disks are healthy"""

    vm = gce.get_instance(project_id=op.get(flags.PROJECT_ID),
                          zone=op.get(flags.ZONE),
                          instance_name=op.get(flags.NAME))

    start_formatted_string = op.get(
        flags.START_TIME).strftime('%Y/%m/%d %H:%M:%S')
    end_formatted_string = op.get(flags.END_TIME).strftime('%Y/%m/%d %H:%M:%S')
    within_str = f'within d\'{start_formatted_string}\', d\'{end_formatted_string}\''

    for disk in vm.disks:
      pd_health_metrics = monitoring.query(
          op.get(flags.PROJECT_ID), """
            fetch gce_instance
              | metric 'compute.googleapis.com/instance/disk/performance_status'
              | filter (metric.performance_status != 'Healthy')
              | filter (resource.instance_id == '{}') &&
                (metric.device_name == '{}')
              | group_by 3m,
                  [value_performance_status_fraction_true:
                    fraction_true(value.performance_status)]
              | every 3m
              | filter value_performance_status_fraction_true > 0
              | {}
            """.format(vm.id, disk['deviceName'], within_str))

      if pd_health_metrics:
        op.add_failed(vm,
                      reason=op.prep_msg(op.FAILURE_REASON,
                                         disk_name=disk['deviceName']),
                      remediation=op.prep_msg(op.FAILURE_REMEDIATION))
      else:
        op.add_ok(vm,
                  reason=op.prep_msg(op.SUCCESS_REASON,
                                     disk_name=disk['deviceName']))


class CpuOvercommitmentCheck(runbook.Step):
  """Checking if CPU overcommited beyond threshold"""

  def execute(self):
    """Checking if CPU is overcommited"""
    cpu_count = 1000
    start_formatted_string = op.get(
        flags.START_TIME).strftime('%Y/%m/%d %H:%M:%S')
    end_formatted_string = op.get(flags.END_TIME).strftime('%Y/%m/%d %H:%M:%S')
    within_str = f'within d\'{start_formatted_string}\', d\'{end_formatted_string}\''

    vm = gce.get_instance(project_id=op.get(flags.PROJECT_ID),
                          zone=op.get(flags.ZONE),
                          instance_name=op.get(flags.NAME))

    if vm.is_sole_tenant_vm or 'e2' in vm.machine_type():

      start_dt_pst = datetime.strptime(vm.laststarttimestamp(),
                                       '%Y-%m-%dT%H:%M:%S.%f%z')
      start_dt_utc = start_dt_pst.astimezone(timezone.utc)
      start_dt_utc_plus_5_mins = start_dt_utc + timedelta(minutes=5)
      current_time_utc = datetime.now(timezone.utc)
      within_hours = 9
      if (start_dt_utc_plus_5_mins > current_time_utc or
          not vm.is_running) and vm.laststoptimestamp():
        # Instance just starting up, CpuCount might not be available currently via metrics.
        # Use instance's last stop time as EndTime for monitoring query
        stop_dt_pst = datetime.strptime(vm.laststoptimestamp(),
                                        '%Y-%m-%dT%H:%M:%S.%f%z')
        stop_dt_utc = stop_dt_pst.astimezone(timezone.utc)
        end_formatted_string = stop_dt_utc.strftime('%Y/%m/%d %H:%M:%S')
        within_str = 'within %dh, d\'%s\'' % (within_hours,
                                              end_formatted_string)
      else:
        within_str = f'within d\'{start_formatted_string}\', d\'{end_formatted_string}\''

      try:
        cpu_count_query = monitoring.query(
            op.get(flags.PROJECT_ID), """
                    fetch gce_instance
                    | metric 'compute.googleapis.com/instance/cpu/guest_visible_vcpus'
                    | filter (resource.instance_id == '{}')
                    | group_by 1m, [value_guest_visible_vcpus_mean:
                        mean(value.guest_visible_vcpus)]
                    | every 1m
                    | group_by [],
                        [value_guest_visible_vcpus_mean_aggregate:
                        aggregate(value_guest_visible_vcpus_mean)]
                    | {}
                """.format(vm.id, within_str))
      except googleapiclient.errors.HttpError:
        op.add_failed(
            op.get(flags.PROJECT_ID),
            reason=('Not able to pull CPU count for instance {}').format(
                op.get(flags.NAME)),
            remediation='')
      else:
        if cpu_count_query:
          cpu_count = int(list(cpu_count_query.values())[0]['values'][0][0])
        else:
          op.info((
              'CPU count info not available for the instance.\n'
              'Please start the VM {} if it is not in running state.\n').format(
                  vm.short_path))
          return

      # an acceptable average Scheduler Wait Time is 20 ms/s per vCPU.
      utilization_threshold = cpu_count * 20

      cpu_overcomit_metrics = monitoring.query(
          op.get(flags.PROJECT_ID), """
                    fetch gce_instance
                    | metric 'compute.googleapis.com/instance/cpu/scheduler_wait_time'
                    | filter (resource.instance_id == '{}')
                    | group_by [resource.instance_id], 1m,
                        [value_scheduler_wait_time_max: max(value.scheduler_wait_time)]
                    | every 1m
                    | filter (cast_units(value_scheduler_wait_time_max,"")*1000) >= {}
                    | {}
                """.format(vm.id, utilization_threshold, within_str))
      if cpu_overcomit_metrics:
        op.add_failed(
            vm,
            reason=
            ('CPU for the VM {} is over committed beyond acceptable limits: {} ms/s'
            ).format(vm.name, utilization_threshold),
            remediation='')
      else:
        op.add_ok(vm, reason='VM CPU is not overcommited.\n')
    else:
      op.add_skipped(vm,
                     reason='VM is neither a Sole Tenent VM nor an E2 instance,'
                     'Skipping CPU Overcommitment checks')


class DiskAvgIOLatencyCheck(runbook.Step):
  """Check Disk Avg IO Latency"""

  template = 'vm_performance::disk_io_latency_check'

  def execute(self):
    """Checking if Instance's Disk Avg IO Latency is within optimal limits"""

    vm = gce.get_instance(project_id=op.get(flags.PROJECT_ID),
                          zone=op.get(flags.ZONE),
                          instance_name=op.get(flags.NAME))

    start_formatted_string = op.get(
        flags.START_TIME).strftime('%Y/%m/%d %H:%M:%S')
    end_formatted_string = op.get(flags.END_TIME).strftime('%Y/%m/%d %H:%M:%S')
    within_str = f'within d\'{start_formatted_string}\', d\'{end_formatted_string}\''

    # Fetch list of disks for the instance
    disk_list = gce.get_all_disks_of_instance(op.get(flags.PROJECT_ID), vm.zone,
                                              vm.name)
    disk: gce.Disk
    for disks in disk_list.items():
      disk = disks[1]
      if disk.type in ['pd-balanced', 'pd-ssd', 'pd-standard', 'pd-extreme']:
        # Checking Disk IO latency for the instance -
        disk_io_latency = monitoring.query(
            op.get(flags.PROJECT_ID), """
          fetch gce_instance
          | metric 'compute.googleapis.com/instance/disk/average_io_latency'
          | filter (resource.instance_id == '{}')
            &&
              (metric.device_name == '{}'
              && metric.storage_type == '{}')
          | group_by 1m, [value_average_io_latency_mean: mean(value.average_io_latency)]
          | every 1m
          | group_by [metric.storage_type],
            [value_average_io_latency_mean_percentile:
            percentile(value_average_io_latency_mean, 99)]
          | filter(cast_units(value_average_io_latency_mean_percentile,"")/1000) >= {}
          | {}
          """.format(vm.id, disk.name, disk.type, IO_LATENCY_THRESHOLD,
                     within_str))

        if disk_io_latency:
          op.add_failed(vm,
                        reason=op.prep_msg(op.FAILURE_REASON,
                                           disk_name=disk.name),
                        remediation=op.prep_msg(op.FAILURE_REMEDIATION))
        else:
          op.add_ok(vm,
                    reason=op.prep_msg(op.SUCCESS_REASON, disk_name=disk.name))
      else:
        op.add_skipped(
            vm,
            reason=('Disk-Type {} is not supported with this gcpdiag runbook,'
                    ' disk name - {}').format(disk.type, disk.name))


class DiskIopsThroughputUtilisationChecks(runbook.Step):
  """Checking if the Disk IOPS/throughput usage is within optimal levels"""

  # IOPS and Throughput calculation is based on -
  # https://cloud.google.com/compute/docs/disks/performance
  template = 'vm_performance::disk_io_usage_check'
  start_time: datetime
  end_time: datetime
  start_formatted_string: datetime
  end_formatted_string: datetime
  silent: bool

  def execute(self):
    """Checking if the Disk IOPS/throughput usage is within optimal levels"""

    if hasattr(self, 'start_time'):
      self.start_formatted_string = self.start_time
    else:
      self.start_formatted_string = op.get(
          flags.START_TIME).strftime('%Y/%m/%d %H:%M:%S')

    if hasattr(self, 'end_time'):
      self.end_formatted_string = self.end_time
    else:
      self.end_formatted_string = op.get(
          flags.END_TIME).strftime('%Y/%m/%d %H:%M:%S')

    #op.info(('\n\nStart TIme: {}, End time: {}\n\n').format(
    #    self.start_formatted_string, self.end_formatted_string))

    disk_io_util_threshold = 0.9

    vm = gce.get_instance(project_id=op.get(flags.PROJECT_ID),
                          zone=op.get(flags.ZONE),
                          instance_name=op.get(flags.NAME))

    start_dt_pst = datetime.strptime(vm.laststarttimestamp(),
                                     '%Y-%m-%dT%H:%M:%S.%f%z')
    start_dt_utc = start_dt_pst.astimezone(timezone.utc)
    start_dt_utc_plus_5_mins = start_dt_utc + timedelta(minutes=5)
    current_time_utc = datetime.now(timezone.utc)
    within_hours = 9
    if (start_dt_utc_plus_5_mins > current_time_utc or
        not vm.is_running) and vm.laststoptimestamp():
      # Instance just starting up, CpuCount might not be available currently via metrics.
      # Use instance's last stop time as EndTime for monitoring query
      stop_dt_pst = datetime.strptime(vm.laststoptimestamp(),
                                      '%Y-%m-%dT%H:%M:%S.%f%z')
      stop_dt_utc = stop_dt_pst.astimezone(timezone.utc)
      end_formatted_string = stop_dt_utc.strftime('%Y/%m/%d %H:%M:%S')
      within_str = 'within %dh, d\'%s\'' % (within_hours, end_formatted_string)
    else:
      within_str = f'within d\'{self.start_formatted_string}\', d\'{self.end_formatted_string}\''

    try:
      cpu_count_query = monitoring.query(
          op.get(flags.PROJECT_ID), """
                fetch gce_instance
                | metric 'compute.googleapis.com/instance/cpu/guest_visible_vcpus'
                | filter (resource.instance_id == '{}')
                | group_by 1m, [value_guest_visible_vcpus_mean:
                    mean(value.guest_visible_vcpus)]
                | every 1m
                | group_by [],
                    [value_guest_visible_vcpus_mean_aggregate:
                    aggregate(value_guest_visible_vcpus_mean)]
                | {}
            """.format(vm.id, within_str))
    except googleapiclient.errors.HttpError:
      op.add_skipped(
          op.get(flags.PROJECT_ID),
          reason=('Not able to pull CPU count for instance {}').format(
              op.get(flags.NAME)))

    if cpu_count_query:
      cpu_count = int(list(cpu_count_query.values())[0]['values'][0][0])
    else:
      op.add_failed(
          vm,
          reason='\tCPU count info is not available for the instance via'
          ' Monitoring metric "guest_visible_vcpus"',
          remediation=(
              '\tPlease first start the VM {}, if it is not in running state'
          ).format(vm.short_path))
      return

    # Fetch list of disks for the instance
    disk_list = gce.get_all_disks_of_instance(op.get(flags.PROJECT_ID), vm.zone,
                                              vm.name)

    # Load limits per GB data from json file
    limits_per_gb_file = f'{dirname(__file__)}/disk_performance_benchmark/limits_per_gb.json'
    with open(limits_per_gb_file, encoding='utf-8') as file:
      limits_data = json.load(file)
    file.close()

    vm_family = vm.machine_type()[0]
    if vm.machine_type().split('-')[0] == 'custom':
      vm_family = 'n'

    # Load instance level iops/throughput limits from json file
    vm_family_file = f'{dirname(__file__)}/disk_performance_benchmark/{vm_family}-family.json'

    with open(vm_family_file, encoding='utf-8') as f:
      mach_fam_json_data = json.load(f)
    f.close()

    # Fetch disk sizes attached to the VM:
    total_disk_size = {
        'pd-balanced': 0,
        'pd-ssd': 0,
        'pd-standard': 0,
        'pd-extreme': 0
    }
    provisions_iops = {
        'pd-balanced': 0,
        'pd-ssd': 0,
        'pd-standard': 0,
        'pd-extreme': 0
    }
    disk: gce.Disk
    for disk_name in disk_list.items():
      disk = disk_name[1]
      if disk.type == 'pd-balanced':
        total_disk_size['pd-balanced'] += int(disk.size)
      elif disk.type == 'pd-ssd':
        total_disk_size['pd-ssd'] += int(disk.size)
      elif disk.type == 'pd-standard':
        total_disk_size['pd-standard'] += int(disk.size)
      elif disk.type == 'pd-extreme':
        total_disk_size['pd-extreme'] += int(disk.size)
        provisions_iops['pd-extreme'] += int(disk.provisionediops or 0)
      else:
        op.add_skipped(
            vm,
            reason=('Disk-Type {} is not supported with this gcpdiag runbook,'
                    ' disk name - {}').format(disk.type, disk.name))

    # Getting dirty with logic based on different disk types, Machine types, CPU counts etc.
    for disktypes in total_disk_size.items():
      disktype = disktypes[0]
      if total_disk_size[disktype] > 0 and cpu_count > 0:

        if vm_family in ['a', 'f', 'g', 'm']:
          if vm.machine_type().split('-')[0].upper() in [
              'A2', 'A3', 'F1', 'G2', 'M1', 'M2', 'M3'
          ]:
            next_hop = 'Machine type'
            next_hop_val = vm.machine_type()
            search_str = vm.machine_type().split('-')[0].upper()
            if search_str == 'A2' and 'ultragpu' in next_hop_val:
              search_str = search_str + ' Ultra VMs'
            elif search_str == 'A2' and 'highgpu' in next_hop_val:
              search_str = search_str + ' Ultra VMs'
            else:
              search_str = search_str + ' VMs'

            data = self.limit_calculator(limits_data,
                                         mach_fam_json_data, disktype,
                                         int(total_disk_size[disktype]),
                                         search_str, next_hop, next_hop_val)

            # upto first 100GB, pd-standard disks have fixed IO limits
            if disktype == 'pd-standard' and int(
                total_disk_size[disktype]) < 100:
              op.info((
                  '\n\tIOPS and Throughput limits available for VM DiskType - {},'
                  '\n\tTotal DiskSize: {}:'
                  '\n\n\t Read-IOPS Count: {},'
                  '\n\t Read-Throughput: {} MB/s,'
                  '\n\t Write-IOPS Count: {},'
                  '\n\t Write-Throughput: {} MB/s\n').format(
                      disktype, int(total_disk_size[disktype]), 75, 12, 150,
                      12))

              self.actual_usage_comparision(vm, disktype,
                                            75 * disk_io_util_threshold,
                                            'max_read_ops_count')
              self.actual_usage_comparision(
                  vm, disktype, 12 * disk_io_util_threshold * 1000 * 1000,
                  'max_read_bytes_count')
              self.actual_usage_comparision(vm, disktype,
                                            150 * disk_io_util_threshold,
                                            'max_write_ops_count')
              self.actual_usage_comparision(
                  vm, disktype, 12 * disk_io_util_threshold * 1000 * 1000,
                  'max_write_bytes_count')

            elif disktype == 'pd-extreme' and vm.machine_type() in [
                'g1-small', 'f1-micro'
            ]:
              op.add_skipped(
                  vm,
                  reason=('The script do not support '
                          'pd-extreme disk type with machine type {} \n'
                         ).format(next_hop_val))
            else:
              op.info(
                  ('IOPS and Throughput limits available for VM DiskType - {},'
                   '\n\tTotal DiskSize: {}:'
                   '\n\n\t Max Read-IOPS Count: {},'
                   '\n\t Max Read-Throughput: {} MB/s,'
                   '\n\t Max Write-IOPS Count: {},'
                   '\n\t Max Write-Throughput: {} MB/s\n').format(
                       disktype, int(total_disk_size[disktype]),
                       min(data[0], data[1]), min(data[2], data[3]),
                       min(data[4], data[5]), min(data[6], data[7])))

              self.actual_usage_comparision(
                  vm, disktype,
                  min(data[0], data[1]) * disk_io_util_threshold,
                  'max_read_ops_count')
              self.actual_usage_comparision(
                  vm, disktype,
                  min(data[2], data[3]) * disk_io_util_threshold * 1000 * 1000,
                  'max_read_bytes_count')
              self.actual_usage_comparision(
                  vm, disktype,
                  min(data[4], data[5]) * disk_io_util_threshold,
                  'max_write_ops_count')
              self.actual_usage_comparision(
                  vm, disktype,
                  min(data[6], data[7]) * disk_io_util_threshold * 1000 * 1000,
                  'max_write_bytes_count')
          else:
            op.add_failed(
                vm,
                reason=
                ('The machine type {} is not supported with this gcpdiag runbook'
                ).format(vm.machine_type()),
                remediation=
                'You may only run this runbook for any of the below machine family:'
                'A2, A3, C2, C2D, C3, C3D, E2, F1, G1, G2,'
                ' H3, N1, N2, N2D, M1, M2, M3, T2D, T2A, Z3')

        elif vm_family in ['c', 'h', 'z']:
          if vm.machine_type().split('-')[0].upper() in [
              'C2', 'C2D', 'C3', 'C3D', 'H3', 'Z3'
          ]:
            next_hop = 'VM vCPU count'
            next_hop_val = str(cpu_count)
            search_str = vm.machine_type().split('-')[0].upper() + ' VMs'

            # upto first 100GB, pd-standard disks have fixed IO limits
            if disktype == 'pd-standard' and int(
                total_disk_size[disktype]) < 100:
              op.info((
                  '\n\tIOPS and Throughput limits available for VM DiskType - {},'
                  '\n\tTotal DiskSize: {}:'
                  '\n\n\t Read-IOPS Count: {},'
                  '\n\t Read-Throughput: {} MB/s,'
                  '\n\t Write-IOPS Count: {},'
                  '\n\t Write-Throughput: {} MB/s\n').format(
                      disktype, int(total_disk_size[disktype]), 75, 12, 150,
                      12))

              self.actual_usage_comparision(vm, disktype,
                                            75 * disk_io_util_threshold,
                                            'max_read_ops_count')
              self.actual_usage_comparision(
                  vm, disktype, 12 * disk_io_util_threshold * 1000 * 1000,
                  'max_read_bytes_count')
              self.actual_usage_comparision(vm, disktype,
                                            150 * disk_io_util_threshold,
                                            'max_write_ops_count')
              self.actual_usage_comparision(
                  vm, disktype, 12 * disk_io_util_threshold * 1000 * 1000,
                  'max_write_bytes_count')

            elif disktype == 'pd-extreme':
              # https://cloud.google.com/compute/docs/disks/extreme-persistent-disk#machine_shape_support

              data = self.limit_calculator(limits_data, mach_fam_json_data,
                                           'pd-ssd',
                                           int(total_disk_size['pd-extreme']),
                                           search_str, next_hop, next_hop_val)

              op.info(
                  ('IOPS and Throughput limits available for VM DiskType - {},'
                   '\n\tTotal DiskSize: {}:'
                   '\n\n\t Max Read-IOPS Count: {},'
                   '\n\t Max Read-Throughput: {} MB/s,'
                   '\n\t Max Write-IOPS Count: {},'
                   '\n\t Max Write-Throughput: {} MB/s\n').format(
                       disktype, int(total_disk_size[disktype]),
                       min(data[1], provisions_iops['pd-extreme']),
                       min(data[2], data[3]),
                       min(data[5], provisions_iops['pd-extreme']),
                       min(data[6], data[7])))

              self.actual_usage_comparision(
                  vm, disktype,
                  min(data[1], provisions_iops['pd-extreme']) *
                  disk_io_util_threshold, 'max_read_ops_count')
              self.actual_usage_comparision(
                  vm, disktype,
                  min(data[2], data[3]) * disk_io_util_threshold * 1000 * 1000,
                  'max_read_bytes_count')
              self.actual_usage_comparision(
                  vm, disktype,
                  min(data[5], provisions_iops['pd-extreme']) * 0.9,
                  'max_write_ops_count')
              self.actual_usage_comparision(
                  vm, disktype,
                  min(data[6], data[7]) * disk_io_util_threshold * 1000 * 1000,
                  'max_write_bytes_count')

            else:
              data = self.limit_calculator(limits_data, mach_fam_json_data,
                                           disktype,
                                           int(total_disk_size[disktype]),
                                           search_str, next_hop, next_hop_val)
              op.info(
                  ('IOPS and Throughput limits available for VM DiskType - {},'
                   '\n\t Total DiskSize: {}:'
                   '\n\n\t Max Read-IOPS Count: {},'
                   '\n\t Max Read-Throughput: {} MB/s,'
                   '\n\t Max Write-IOPS Count: {},'
                   '\n\t Max Write-Throughput: {} MB/s\n').format(
                       disktype, int(total_disk_size[disktype]),
                       min(data[0], data[1]), min(data[2], data[3]),
                       min(data[4], data[5]), min(data[6], data[7])))

              self.actual_usage_comparision(
                  vm, disktype,
                  min(data[0], data[1]) * disk_io_util_threshold,
                  'max_read_ops_count')
              self.actual_usage_comparision(
                  vm, disktype,
                  min(data[2], data[3]) * disk_io_util_threshold * 1000 * 1000,
                  'max_read_bytes_count')
              self.actual_usage_comparision(
                  vm, disktype,
                  min(data[4], data[5]) * disk_io_util_threshold,
                  'max_write_ops_count')
              self.actual_usage_comparision(
                  vm, disktype,
                  min(data[6], data[7]) * disk_io_util_threshold * 1000 * 1000,
                  'max_write_bytes_count')
          else:
            op.add_failed(
                vm,
                reason=
                ('The machine type {} is not supported with this gcpdiag runbook'
                ).format(vm.machine_type()),
                remediation=
                'You may only run this runbook for any of the below machine family:'
                'A2, A3, C2, C2D, C3, C3D, E2, F1, G1, G2,'
                ' H3, N1, N2, N2D, M1, M2, M3, T2D, T2A, Z3')

        elif vm_family == 't':
          # Logic to fetch details for T2 family type
          if vm.machine_type().split('-')[0].upper() in ['T2D', 'T2A']:
            next_hop = 'VM vCPU count'
            if vm.machine_type().split('-')[0].upper() == 'T2D':
              # T2D Family
              if disktype == 'pd-standard':
                if cpu_count == 1:
                  next_hop_val = '1'
                elif cpu_count in range(2, 8):
                  next_hop_val = '2-7'
                elif cpu_count in range(8, 16):
                  next_hop_val = '8-15'
                elif cpu_count > 15:
                  next_hop_val = '16 or more'
              else:
                if cpu_count == 1:
                  next_hop_val = '1'
                elif cpu_count in range(2, 8):
                  next_hop_val = '2-7'
                elif cpu_count in range(8, 16):
                  next_hop_val = '8-15'
                elif cpu_count in range(16, 32):
                  next_hop_val = '16-31'
                elif cpu_count > 31:
                  next_hop_val = '32-60'
            else:
              # T2A Family
              if disktype == 'pd-standard':
                if cpu_count == 1:
                  next_hop_val = '1'
                elif cpu_count in range(2, 4):
                  next_hop_val = '2-3'
                elif cpu_count in range(4, 8):
                  next_hop_val = '4-7'
                elif cpu_count in range(8, 16):
                  next_hop_val = '8-15'
                elif cpu_count > 15:
                  next_hop_val = '16 or more'
              else:
                if cpu_count == 1:
                  next_hop_val = '1'
                elif cpu_count in range(2, 8):
                  next_hop_val = '2-7'
                elif cpu_count in range(8, 16):
                  next_hop_val = '8-15'
                elif cpu_count in range(16, 32):
                  next_hop_val = '16-31'
                elif cpu_count in range(32, 48):
                  next_hop_val = '32-47'
                elif cpu_count > 47:
                  next_hop_val = '48'

            search_str = vm.machine_type().split('-')[0].upper() + ' VMs'

            if disktype == 'pd-extreme':
              # https://cloud.google.com/compute/docs/disks/extreme-persistent-disk#machine_shape_support

              data = self.limit_calculator(limits_data, mach_fam_json_data,
                                           'pd-ssd',
                                           int(total_disk_size['pd-extreme']),
                                           search_str, next_hop, next_hop_val)

              op.info(
                  ('IOPS and Throughput limits available for VM DiskType - {},'
                   '\n\tTotal DiskSize: {}:'
                   '\n\n\t Max Read-IOPS Count: {},'
                   '\n\t Max Read-Throughput: {} MB/s,'
                   '\n\t Max Write-IOPS Count: {},'
                   '\n\t Max Write-Throughput: {} MB/s\n').format(
                       disktype, int(total_disk_size[disktype]),
                       min(data[1], provisions_iops['pd-extreme']),
                       min(data[2], data[3]),
                       min(data[5], provisions_iops['pd-extreme']),
                       min(data[6], data[7])))

              self.actual_usage_comparision(
                  vm, disktype,
                  min(data[1], provisions_iops['pd-extreme']) *
                  disk_io_util_threshold, 'max_read_ops_count')
              self.actual_usage_comparision(
                  vm, disktype,
                  min(data[2], data[3]) * disk_io_util_threshold * 1000 * 1000,
                  'max_read_bytes_count')
              self.actual_usage_comparision(
                  vm, disktype,
                  min(data[5], provisions_iops['pd-extreme']) * 0.9,
                  'max_write_ops_count')
              self.actual_usage_comparision(
                  vm, disktype,
                  min(data[6], data[7]) * disk_io_util_threshold * 1000 * 1000,
                  'max_write_bytes_count')

            elif disktype == 'pd-standard' and int(
                total_disk_size[disktype]) < 100:
              # upto first 100GB, pd-standard disks have fixed IO limits
              op.info((
                  '\n\tIOPS and Throughput limits available for VM DiskType - {},'
                  '\n\tTotal DiskSize: {}:'
                  '\n\n\t Read-IOPS Count: {},'
                  '\n\t Read-Throughput: {} MB/s,'
                  '\n\t Write-IOPS Count: {},'
                  '\n\t Write-Throughput: {} MB/s\n').format(
                      disktype, int(total_disk_size[disktype]), 75, 12, 150,
                      12))

              self.actual_usage_comparision(vm, disktype,
                                            75 * disk_io_util_threshold,
                                            'max_read_ops_count')
              self.actual_usage_comparision(
                  vm, disktype, 12 * disk_io_util_threshold * 1000 * 1000,
                  'max_read_bytes_count')
              self.actual_usage_comparision(vm, disktype,
                                            150 * disk_io_util_threshold,
                                            'max_write_ops_count')
              self.actual_usage_comparision(
                  vm, disktype, 12 * disk_io_util_threshold * 1000 * 1000,
                  'max_write_bytes_count')

            else:
              data = self.limit_calculator(limits_data, mach_fam_json_data,
                                           disktype,
                                           int(total_disk_size[disktype]),
                                           search_str, next_hop, next_hop_val)

              op.info(
                  ('IOPS and Throughput limits available for VM DiskType - {},'
                   '\n\tTotal DiskSize: {}:'
                   '\n\n\t Max Read-IOPS Count: {},'
                   '\n\t Max Read-Throughput: {} MB/s,'
                   '\n\t Max Write-IOPS Count: {},'
                   '\n\t Max Write-Throughput: {} MB/s\n').format(
                       disktype, int(total_disk_size[disktype]),
                       min(data[0], data[1]), min(data[2], data[3]),
                       min(data[4], data[5]), min(data[6], data[7])))

              self.actual_usage_comparision(
                  vm, disktype,
                  min(data[0], data[1]) * disk_io_util_threshold,
                  'max_read_ops_count')
              self.actual_usage_comparision(
                  vm, disktype,
                  min(data[2], data[3]) * disk_io_util_threshold * 1000 * 1000,
                  'max_read_bytes_count')
              self.actual_usage_comparision(
                  vm, disktype,
                  min(data[4], data[5]) * disk_io_util_threshold,
                  'max_write_ops_count')
              self.actual_usage_comparision(
                  vm, disktype,
                  min(data[6], data[7]) * disk_io_util_threshold * 1000 * 1000,
                  'max_write_bytes_count')
          else:
            op.add_failed(
                vm,
                reason=
                ('The machine type {} is not supported with this gcpdiag runbook'
                ).format(vm.machine_type()),
                remediation=
                'You may only run this runbook for any of the below machine family:'
                'A2, A3, C2, C2D, C3, C3D, E2, F1, G1, G2,'
                ' H3, N1, N2, N2D, M1, M2, M3, T2D, T2A, Z3')

        elif vm_family == 'e':
          # Logic to fetch details for E2 family type
          if vm.machine_type().split('-')[0].upper() in ['E2']:
            next_hop = 'VM vCPU count'
            if 'e2-medium' in vm.machine_type():
              next_hop_val = 'e2-medium*'
            else:
              if cpu_count == 1:
                next_hop_val = '1'
              elif cpu_count in range(2, 8):
                next_hop_val = '2-7'
              elif cpu_count in range(8, 16):
                next_hop_val = '8-15'
              elif cpu_count in range(16, 32):
                next_hop_val = '16-31'
              elif cpu_count > 31:
                next_hop_val = '32 or more'
            search_str = vm.machine_type().split('-')[0].upper() + ' VMs'

            if disktype == 'pd-extreme':
              # https://cloud.google.com/compute/docs/disks/extreme-persistent-disk#machine_shape_support

              data = self.limit_calculator(limits_data, mach_fam_json_data,
                                           'pd-ssd',
                                           int(total_disk_size['pd-extreme']),
                                           search_str, next_hop, next_hop_val)

              op.info(
                  ('IOPS and Throughput limits available for VM DiskType - {},'
                   '\n\tTotal DiskSize: {}:'
                   '\n\n\t Max Read-IOPS Count: {},'
                   '\n\t Max Read-Throughput: {} MB/s,'
                   '\n\t Max Write-IOPS Count: {},'
                   '\n\t Max Write-Throughput: {} MB/s\n').format(
                       disktype, int(total_disk_size[disktype]),
                       min(data[1], provisions_iops['pd-extreme']),
                       min(data[2], data[3]),
                       min(data[5], provisions_iops['pd-extreme']),
                       min(data[6], data[7])))

              self.actual_usage_comparision(
                  vm, disktype,
                  min(data[1], provisions_iops['pd-extreme']) *
                  disk_io_util_threshold, 'max_read_ops_count')
              self.actual_usage_comparision(
                  vm, disktype,
                  min(data[2], data[3]) * disk_io_util_threshold * 1000 * 1000,
                  'max_read_bytes_count')
              self.actual_usage_comparision(
                  vm, disktype,
                  min(data[5], provisions_iops['pd-extreme']) *
                  disk_io_util_threshold, 'max_write_ops_count')
              self.actual_usage_comparision(
                  vm, disktype,
                  min(data[6], data[7]) * disk_io_util_threshold * 1000 * 1000,
                  'max_write_bytes_count')

            elif disktype == 'pd-standard' and int(
                total_disk_size[disktype]) < 100:
              # upto first 100GB, pd-standard disks have fixed IO limits
              op.info((
                  '\n\tIOPS and Throughput limits available for VM DiskType - {},'
                  '\n\tTotal DiskSize: {}:'
                  '\n\n\t Read-IOPS Count: {},'
                  '\n\t Read-Throughput: {} MB/s,'
                  '\n\t Write-IOPS Count: {},'
                  '\n\t Write-Throughput: {} MB/s\n').format(
                      disktype, int(total_disk_size[disktype]), 75, 12, 150,
                      12))

              self.actual_usage_comparision(vm, disktype,
                                            75 * disk_io_util_threshold,
                                            'max_read_ops_count')
              self.actual_usage_comparision(
                  vm, disktype, 12 * disk_io_util_threshold * 1000 * 1000,
                  'max_read_bytes_count')
              self.actual_usage_comparision(vm, disktype,
                                            150 * disk_io_util_threshold,
                                            'max_write_ops_count')
              self.actual_usage_comparision(
                  vm, disktype, 12 * disk_io_util_threshold * 1000 * 1000,
                  'max_write_bytes_count')
            else:
              data = self.limit_calculator(limits_data, mach_fam_json_data,
                                           disktype,
                                           int(total_disk_size[disktype]),
                                           search_str, next_hop, next_hop_val)

              op.info(
                  ('IOPS and Throughput limits available for VM DiskType - {},'
                   '\n\tTotal DiskSize: {}:'
                   '\n\n\t Max Read-IOPS Count: {},'
                   '\n\t Max Read-Throughput: {} MB/s,'
                   '\n\t Max Write-IOPS Count: {},'
                   '\n\t Max Write-Throughput: {} MB/s\n').format(
                       disktype, int(total_disk_size[disktype]),
                       min(data[0], data[1]), min(data[2], data[3]),
                       min(data[4], data[5]), min(data[6], data[7])))

              self.actual_usage_comparision(
                  vm, disktype,
                  min(data[0], data[1]) * disk_io_util_threshold,
                  'max_read_ops_count')
              self.actual_usage_comparision(
                  vm, disktype,
                  min(data[2], data[3]) * disk_io_util_threshold * 1000 * 1000,
                  'max_read_bytes_count')
              self.actual_usage_comparision(
                  vm, disktype,
                  min(data[4], data[5]) * disk_io_util_threshold,
                  'max_write_ops_count')
              self.actual_usage_comparision(
                  vm, disktype,
                  min(data[6], data[7]) * disk_io_util_threshold * 1000 * 1000,
                  'max_write_bytes_count')
          else:
            op.add_failed(
                vm,
                reason=
                ('The machine type {} is not supported with this gcpdiag runbook'
                ).format(vm.machine_type()),
                remediation=
                'You may only run this runbook for any of the below machine family:'
                'A2, A3, C2, C2D, C3, C3D, E2, F1, G1, G2,'
                ' H3, N1, N2, N2D, M1, M2, M3, T2D, T2A, Z3')

        elif vm_family == 'n':
          if vm.machine_type().split('-')[0].upper() in [
              'N1', 'N2', 'N2D', 'CUSTOM'
          ]:
            next_hop = 'VM vCPU count'
            if vm.machine_type().split('-')[0] == 'custom':
              search_str = 'N1 VMs'
            else:
              search_str = vm.machine_type().split('-')[0].upper() + ' VMs'
            if disktype in ['pd-balanced', 'pd-ssd']:
              if cpu_count == 1:
                next_hop_val = '1'
              elif cpu_count in range(2, 8):
                next_hop_val = '2-7'
              elif cpu_count in range(8, 16):
                next_hop_val = '8-15'
              elif cpu_count in range(16, 32):
                next_hop_val = '16-31'
              elif cpu_count in range(32, 64):
                next_hop_val = '32-63'
              elif cpu_count > 63:
                next_hop_val = '64 or more'

              data = self.limit_calculator(limits_data, mach_fam_json_data,
                                           disktype,
                                           int(total_disk_size[disktype]),
                                           search_str, next_hop, next_hop_val)
              op.info((
                  'IOPS and Throughput limits available for VM DiskType - {}, Total DiskSize: {}:'
                  '\n\n\t Max Read-IOPS Count: {}, \n\t Max Read-Throughput: {} MB/s,'
                  '\n\t Max Write-IOPS Count: {}, \n\t Max Write-Throughput: {} MB/s'
              ).format(disktype, int(total_disk_size[disktype]),
                       min(data[0], data[1]), min(data[2], data[3]),
                       min(data[4], data[5]), min(data[6], data[7])))

              self.actual_usage_comparision(
                  vm, disktype,
                  min(data[0], data[1]) * disk_io_util_threshold,
                  'max_read_ops_count')
              self.actual_usage_comparision(
                  vm, disktype,
                  min(data[2], data[3]) * disk_io_util_threshold * 1000 * 1000,
                  'max_read_bytes_count')
              self.actual_usage_comparision(
                  vm, disktype,
                  min(data[4], data[5]) * disk_io_util_threshold,
                  'max_write_ops_count')
              self.actual_usage_comparision(
                  vm, disktype,
                  min(data[6], data[7]) * disk_io_util_threshold * 1000 * 1000,
                  'max_write_bytes_count')

            elif disktype == 'pd-standard':
              if cpu_count == 1:
                next_hop_val = '1'
              elif cpu_count in range(2, 8):
                next_hop_val = '2-7'
              elif cpu_count in range(8, 16):
                next_hop_val = '8-15'
              elif cpu_count > 15:
                next_hop_val = '16 or more'

              if int(total_disk_size[disktype]) < 100:
                # upto first 100GB, pd-standard disks have fixed IO limits
                op.info((
                    '\n\tIOPS and Throughput limits available for VM DiskType - {},'
                    '\n\tTotal DiskSize: {}:'
                    '\n\n\t Read-IOPS Count: {},'
                    '\n\t Read-Throughput: {} MB/s,'
                    '\n\t Write-IOPS Count: {},'
                    '\n\t Write-Throughput: {} MB/s\n').format(
                        disktype, int(total_disk_size[disktype]), 75, 12, 150,
                        12))

                self.actual_usage_comparision(vm, disktype,
                                              75 * disk_io_util_threshold,
                                              'max_read_ops_count')
                self.actual_usage_comparision(
                    vm, disktype, 12 * disk_io_util_threshold * 1000 * 1000,
                    'max_read_bytes_count')
                self.actual_usage_comparision(vm, disktype,
                                              150 * disk_io_util_threshold,
                                              'max_write_ops_count')
                self.actual_usage_comparision(
                    vm, disktype, 12 * disk_io_util_threshold * 1000 * 1000,
                    'max_write_bytes_count')
              else:
                data = self.limit_calculator(limits_data, mach_fam_json_data,
                                             disktype,
                                             int(total_disk_size[disktype]),
                                             search_str, next_hop, next_hop_val)

                op.info((
                    'IOPS and Throughput limits available for VM DiskType - {},'
                    '\n\tTotal DiskSize: {}:,'
                    '\n\n\t Max Read-IOPS Count: {},'
                    '\n\t Max Read-Throughput: {} MB/s,'
                    '\n\t Max Write-IOPS Count: {},'
                    '\n\t Max Write-Throughput: {} MB/s\n').format(
                        disktype, int(total_disk_size[disktype]),
                        min(data[0], data[1]), min(data[2], data[3]),
                        min(data[4], data[5]), min(data[6], data[7])))

                self.actual_usage_comparision(
                    vm, disktype,
                    min(data[0], data[1]) * disk_io_util_threshold,
                    'max_read_ops_count')
                self.actual_usage_comparision(
                    vm, disktype,
                    min(data[2], data[3]) * disk_io_util_threshold * 1000 *
                    1000, 'max_read_bytes_count')
                self.actual_usage_comparision(
                    vm, disktype,
                    min(data[4], data[5]) * disk_io_util_threshold,
                    'max_write_ops_count')
                self.actual_usage_comparision(
                    vm, disktype,
                    min(data[6], data[7]) * disk_io_util_threshold * 1000 *
                    1000, 'max_write_bytes_count')

            elif disktype == 'pd-extreme':
              if search_str == 'N2 VMs' and cpu_count > 63:
                next_hop = 'Machine type'
                next_hop_val = vm.machine_type()
                data = self.limit_calculator(limits_data, mach_fam_json_data,
                                             disktype,
                                             int(total_disk_size[disktype]),
                                             search_str, next_hop, next_hop_val)

                op.info((
                    'IOPS and Throughput limits available for VM DiskType - {},'
                    '\n\tTotal DiskSize: {}:'
                    '\n\n\t Max Read-IOPS Count: {},'
                    '\n\t Max Read-Throughput: {} MB/s,'
                    '\n\t Max Write-IOPS Count: {},'
                    '\n\t Max Write-Throughput: {} MB/s\n').format(
                        disktype, int(total_disk_size[disktype]),
                        min(data[1], provisions_iops['pd-extreme']),
                        min(data[2], data[3]),
                        min(data[5], provisions_iops['pd-extreme']),
                        min(data[6], data[7])))

                self.actual_usage_comparision(
                    vm, disktype,
                    min(data[1], provisions_iops['pd-extreme']) *
                    disk_io_util_threshold, 'max_read_ops_count')
                self.actual_usage_comparision(
                    vm, disktype,
                    min(data[2], data[3]) * disk_io_util_threshold * 1000 *
                    1000, 'max_read_bytes_count')
                self.actual_usage_comparision(
                    vm, disktype,
                    min(data[5], provisions_iops['pd-extreme']) *
                    disk_io_util_threshold, 'max_write_ops_count')
                self.actual_usage_comparision(
                    vm, disktype,
                    min(data[6], data[7]) * disk_io_util_threshold * 1000 *
                    1000, 'max_write_bytes_count')
              else:
                next_hop = 'VM vCPU count'
                data = self.limit_calculator(limits_data, mach_fam_json_data,
                                             'pd-ssd',
                                             int(total_disk_size['pd-extreme']),
                                             search_str, next_hop, next_hop_val)
                # https://cloud.google.com/compute/docs/disks/extreme-persistent-disk#machine_shape_support
                op.info((
                    'IOPS and Throughput limits available for VM DiskType - {},'
                    '\n\tTotal DiskSize: {}:'
                    '\n\n\t Max Read-IOPS Count: {},'
                    '\n\t Max Read-Throughput: {} MB/s,'
                    '\n\t Max Write-IOPS Count: {},'
                    '\n\t Max Write-Throughput: {} MB/s\n').format(
                        disktype, int(total_disk_size[disktype]),
                        min(data[1], provisions_iops['pd-extreme']),
                        max(data[2], data[3]),
                        min(data[5], provisions_iops['pd-extreme']),
                        max(data[6], data[7])))

                self.actual_usage_comparision(
                    vm, disktype,
                    min(data[1], provisions_iops['pd-extreme']) *
                    disk_io_util_threshold, 'max_read_ops_count')
                self.actual_usage_comparision(
                    vm, disktype,
                    max(data[2], data[3]) * disk_io_util_threshold * 1000 *
                    1000, 'max_read_bytes_count')
                self.actual_usage_comparision(
                    vm, disktype,
                    min(data[5], provisions_iops['pd-extreme']) *
                    disk_io_util_threshold, 'max_write_ops_count')
                self.actual_usage_comparision(
                    vm, disktype,
                    max(data[6], data[7]) * disk_io_util_threshold * 1000 *
                    1000, 'max_write_bytes_count')
          else:
            op.add_failed(
                vm,
                reason=
                ('The machine type {} is not supported with this gcpdiag runbook'
                ).format(vm.machine_type()),
                remediation=
                'You may only run this runbook for any of the below machine family:'
                'A2, A3, C2, C2D, C3, C3D, E2, F1, G1, G2,'
                ' H3, N1, N2, N2D, M1, M2, M3, T2D, T2A, Z3')
        else:
          op.add_failed(
              vm,
              reason=
              ('The machine type {} is not supported with this gcpdiag runbook'
              ).format(vm.machine_type()),
              remediation=
              'You may only run this runbook for any of the below machine family:'
              'A, C, E, G, F, H, N, M, T, Z')

  def limit_calculator(self, limits_data, mach_fam_json_data, disktype: str,
                       total_disk_size: int, search_str: str, next_hop: str,
                       next_hop_val: str):

    # Data fetch for limits per GB and Baseline
    r_iops_limit_per_gb = float(
        limits_data['iops'][disktype]['Read IOPS per GiB'])
    w_iops_limit_per_gb = float(
        limits_data['iops'][disktype]['Write IOPS per GiB'])
    r_throughput_limit_per_gb = float(
        limits_data['throughput'][disktype]['Throughput per GiB (MiBps)'])
    w_throughput_limit_per_gb = float(
        limits_data['throughput'][disktype]['Throughput per GiB (MiBps)'])
    baseline_iops = float(
        limits_data['baseline'][disktype]['Baseline IOPS per VM'])
    baseline_throughput = float(
        limits_data['baseline'][disktype]['Baseline Throughput (MiBps) per VM'])

    # Calculating VM Baseline performance
    vm_baseline_performance_r_iops = baseline_iops + (r_iops_limit_per_gb *
                                                      total_disk_size)
    vm_baseline_performance_w_iops = baseline_iops + (w_iops_limit_per_gb *
                                                      total_disk_size)
    vm_baseline_performance_r_throughput = baseline_throughput + (
        r_throughput_limit_per_gb * total_disk_size)
    vm_baseline_performance_w_throughput = baseline_throughput + (
        w_throughput_limit_per_gb * total_disk_size)

    max_read_throuput = 10000000
    max_write_throuput = 10000000
    max_read_iops = 10000000
    max_write_iops = 10000000
    for mach_fam_catagory in mach_fam_json_data:
      if search_str and search_str in mach_fam_catagory:
        for item in mach_fam_json_data[mach_fam_catagory][disktype]:
          if item[next_hop] == next_hop_val:
            max_write_iops = item['Maximum write IOPS']
            max_read_iops = item['Maximum read IOPS']
            max_read_throuput = item['Maximum read throughput (MiBps)']
            max_write_throuput = item['Maximum write throughput (MiBps)']

    return (vm_baseline_performance_r_iops, max_read_iops,
            vm_baseline_performance_r_throughput, max_read_throuput,
            vm_baseline_performance_w_iops, max_write_iops,
            vm_baseline_performance_w_throughput, max_write_throuput)

  def actual_usage_comparision(self, vm: gce.Instance, disktype: str,
                               utilization_threshold: float, metric_name: str):

    mon_within_str = f'within d\'{self.start_formatted_string}\', d\'{self.end_formatted_string}\''

    if disktype == 'pd-balanced':
      storage_type = 'PD-Balanced'
    elif disktype == 'pd-extreme':
      storage_type = 'PD-Extreme'
    else:
      storage_type = disktype

    project = crm.get_project(op.get(flags.PROJECT_ID))
    try:
      metric_name_value = metric_name
      comp = monitoring.query(
          op.get(flags.PROJECT_ID), """
                    fetch gce_instance
                    | metric 'compute.googleapis.com/instance/disk/{}'
                    | filter
                        (resource.instance_id == '{}') && (metric.storage_type == '{}')
                    | group_by 1m, [value_max_count: max(value.{})]
                    | every 1m
                    | group_by [],
                        [value_max_count_max_max: max(value_max_count)]
                    | filter value_max_count_max_max >= {}
                    | {}
                    """.format(metric_name, vm.id, storage_type,
                               metric_name_value, utilization_threshold,
                               mon_within_str))
    except googleapiclient.errors.HttpError:
      op.add_skipped(
          project,
          reason=
          ('Not able to fetch monitoring metric {} data for VM {} - Disktype - {}'
          ).format(metric_name, op.get(flags.NAME), disktype))
    else:
      if comp:
        for compval in comp.items():
          if len(compval[1]['values']) > 2:
            op.add_failed(
                vm,
                reason=
                ('{} usage is reaching beyond optimal limits for disk type {} for this VM'
                ).format(metric_name, storage_type),
                remediation=op.prep_msg(op.FAILURE_REMEDIATION,
                                        full_resource_path=vm.full_path,
                                        status=vm.status))
          else:
            op.add_ok(
                vm,
                reason=(
                    '{} usage is within optimal limits for disktype {}').format(
                        metric_name, storage_type))
      else:
        op.add_ok(
            vm,
            reason=('{} usage is within optimal limits for disktype {}').format(
                metric_name, storage_type))


class VmPerformanceEnd(runbook.EndStep):
  """Finalize VM performance diagnostics."""

  def execute(self):
    """Finalize VM performance diagnostics."""
    response = None
    if not config.get(flags.INTERACTIVE_MODE):
      response = op.prompt(
          kind=op.CONFIRMATION,
          message=
          f'Are you able to find issues related to {op.get(flags.NAME)} ?',
          choice_msg='Enter an option: ')
    if response == op.NO:
      op.info(message=op.END_MESSAGE)
