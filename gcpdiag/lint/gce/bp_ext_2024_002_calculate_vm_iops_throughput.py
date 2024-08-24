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
""" Calculate Google Compute Engine VM's IOPS and Throughput Limits

This lint rules provide an easy method to calculate the Instance's
disk IOPS and Throughput applicable max limits.
"""

import json
from datetime import datetime, timedelta, timezone

import googleapiclient

from gcpdiag import lint, models
from gcpdiag.queries import gce, monitoring

vms = None
project = None
instances: list


def prepare_rule(context: models.Context):
  global instances
  instances = [
      vms for vms in gce.get_instances(context).values()
      if not vms.is_gke_node()
  ]


def run_rule(context: models.Context, report: lint.LintReportRuleInterface):
  """Calculating Instance's disk IOPS and Throughput limits"""
  if not instances:
    report.add_skipped(None, 'no instances found')
    return

  vm: gce.Instance
  for vm in sorted(instances):
    if not vm.is_running:
      report.add_skipped(vm, reason=f'VM {vm.name} is in {vm.status} state')
    else:
      # IOPS and Throughput calculation is based on -
      # https://cloud.google.com/compute/docs/disks/performance

      start_dt_pst = datetime.strptime(vm.laststarttimestamp(),
                                       '%Y-%m-%dT%H:%M:%S.%f%z')
      start_dt_utc = start_dt_pst.astimezone(timezone.utc)
      start_dt_utc_plus_10_mins = start_dt_utc + timedelta(minutes=5)
      current_time_utc = datetime.now(timezone.utc)
      within_hours = 9
      if start_dt_utc_plus_10_mins > current_time_utc and (isinstance(
          vm.laststoptimestamp(), str)):
        # Instance just starting up, CpuCount might not be available currently via metrics.
        # Use instance's last stop time as EndTime for monitoring query
        stop_dt_pst = datetime.strptime(vm.laststoptimestamp(),
                                        '%Y-%m-%dT%H:%M:%S.%f%z')
        stop_dt_utc = stop_dt_pst.astimezone(timezone.utc)
        end_formatted_string = stop_dt_utc.strftime('%Y/%m/%d %H:%M:%S')
        within_str = 'within %dh, d\'%s\'' % (within_hours,
                                              end_formatted_string)
      else:
        within_str = 'within %dh, d\'%s\'' % (within_hours,
                                              monitoring.period_aligned_now(5))
      try:
        cpu_count_query = monitoring.query(
            context.project_id, """
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
        report.add_skipped(
            resource=None,
            reason=('Not able to pull CPU count for instance {}').format(vm))

      if cpu_count_query:
        cpu_count = int(list(cpu_count_query.values())[0]['values'][0][0])
      else:
        report.add_skipped(
            vm,
            reason='\tCPU count info is not available for the instance via'
            ' Monitoring metric "guest_visible_vcpus"',
            short_info=(
                '\n\tPlease first start the VM {}, if it is not in running state'
            ).format(vm.short_path))
        return

      # Fetch list of disks for the instance
      disk_list = gce.get_all_disks_of_instance(context.project_id, vm.zone,
                                                vm.name)

      # Load limits per GB data from json file
      limits_per_gb_file = 'gcpdiag/runbook/gce/disk_performance_benchmark/limits_per_gb.json'
      with open(limits_per_gb_file, encoding='utf-8') as file:
        limits_data = json.load(file)
      file.close()

      vm_family = vm.machine_type()[0]

      # Load instance level iops/throughput limits from json file
      machine_family_json_file = (
          'gcpdiag/runbook/gce/disk_performance_benchmark/{}-family.json'
      ).format(vm_family)
      with open(machine_family_json_file, encoding='utf-8') as f:
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
          report.add_skipped(
              vm,
              reason=('Disk-Type {} is not supported with this gcpdiag runbook,'
                      ' disk name - {}').format(disk.type, disk.name))

      # Getting dirty with logic based on different disk types, Machine types, CPU counts etc.
      for disktypes in total_disk_size.items():
        disktype = disktypes[0]
        if total_disk_size[disktype] > 0 and cpu_count > 0:

          if vm_family in ['a', 'f', 'g', 'm']:
            if vm.machine_type().split('-')[0].upper() in [
                'A2', 'A3', 'F1', 'G1', 'G2', 'M1', 'M2', 'M3'
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

              data = limit_calculator(limits_data, mach_fam_json_data, disktype,
                                      int(total_disk_size[disktype]),
                                      search_str, next_hop, next_hop_val)

              # upto first 100GB, pd-standard disks have fixed IO limits
              if disktype == 'pd-standard' and int(
                  total_disk_size[disktype]) < 100:
                report.add_ok(
                    vm,
                    short_info=
                    ('\n\tIOPS and Throughput limits available for VM DiskType - {},'
                     '\n\tTotal DiskSize: {}:'
                     '\n\n\t Max Read-IOPS Count: {}, \n\t Max Read-Throughput: {} MB/s,'
                     '\n\t Max Write-IOPS Count: {}, \n\t Max Write-Throughput: {} MB/s\n'
                    ).format(disktype, int(total_disk_size[disktype]), 75, 12,
                             150, 12))

              elif disktype == 'pd-extreme' and vm.machine_type() in [
                  'g1-small', 'f1-micro'
              ]:
                report.add_skipped(
                    vm,
                    reason=('The script do not support '
                            'pd-extreme disk type with machine type {} \n'
                           ).format(next_hop_val))
              else:
                report.add_ok(
                    vm,
                    short_info=
                    ('\n\tIOPS and Throughput limits available for VM DiskType - {},'
                     '\n\tTotal DiskSize: {}:'
                     '\n\n\t Max Read-IOPS Count: {}, \n\t Max Read-Throughput: {} MB/s,'
                     '\n\t Max Write-IOPS Count: {}, \n\t Max Write-Throughput: {} MB/s\n'
                    ).format(disktype, int(total_disk_size[disktype]),
                             min(data[0], data[1]), min(data[2], data[3]),
                             min(data[4], data[5]), min(data[6], data[7])))

            else:
              report.add_skipped(
                  vm,
                  reason=
                  ('The machine type {} is not supported with this gcpdiag Lint rule'
                   'You may only run this runbook for any of the below machine family:'
                   'A2, A3, C2, C2D, C3, C3D, E2, F1, G1, G2, H3, N1, N2, N2D, M1,'
                   ' M2, M3, T2D, T2A, Z3').format(vm.machine_type()))

          elif vm_family in ['c', 'h', 'z']:
            if vm.machine_type().split('-')[0].upper() in [
                'C2', 'C2D', 'C3', 'C3D', 'H3', 'Z3'
            ]:
              next_hop = 'VM vCPU count'
              next_hop_val = str(cpu_count)
              search_str = vm.machine_type().split('-')[0].upper() + ' VMs'

              data = limit_calculator(limits_data, mach_fam_json_data, disktype,
                                      int(total_disk_size[disktype]),
                                      search_str, next_hop, next_hop_val)
              # upto first 100GB, pd-standard disks have fixed IO limits
              if disktype == 'pd-standard' and int(
                  total_disk_size[disktype]) < 100:
                report.add_ok(
                    vm,
                    short_info=
                    ('\n\tIOPS and Throughput limits available for VM DiskType - {},'
                     '\n\tTotal DiskSize: {}:'
                     '\n\n\t Max Read-IOPS Count: {}, \n\t Max Read-Throughput: {} MB/s,'
                     '\n\t Max Write-IOPS Count: {}, \n\t Max Write-Throughput: {} MB/s\n'
                    ).format(disktype, int(total_disk_size[disktype]), 75, 12,
                             150, 12))
              elif disktype == 'pd-extreme':
                # https://cloud.google.com/compute/docs/disks/extreme-persistent-disk#machine_shape_support
                data = limit_calculator(limits_data, mach_fam_json_data,
                                        'pd-ssd',
                                        int(total_disk_size['pd-extreme']),
                                        search_str, next_hop, next_hop_val)

                report.add_ok(
                    vm,
                    short_info=
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
              else:
                report.add_ok(
                    vm,
                    short_info=
                    ('\n\tIOPS and Throughput limits available for VM DiskType - {},'
                     '\n\tTotal DiskSize: {}:'
                     '\n\n\t Max Read-IOPS Count: {}, \n\t Max Read-Throughput: {} MB/s,'
                     '\n\t Max Write-IOPS Count: {}, \n\t Max Write-Throughput: {} MB/s\n'
                    ).format(disktype, int(total_disk_size[disktype]),
                             min(data[0], data[1]), min(data[2], data[3]),
                             min(data[4], data[5]), min(data[6], data[7])))

            else:
              report.add_skipped(
                  vm,
                  reason=
                  ('The machine type {} is not supported with this gcpdiag Lint rule'
                   'You may only run this runbook for any of the below machine family:'
                   'A2, A3, C2, C2D, C3, C3D, E2, F1, G1, G2, H3, N1, N2, N2D, M1,'
                   ' M2, M3, T2D, T2A, Z3').format(vm.machine_type()))

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

                data = limit_calculator(limits_data, mach_fam_json_data,
                                        'pd-ssd',
                                        int(total_disk_size['pd-extreme']),
                                        search_str, next_hop, next_hop_val)

                report.add_ok(
                    vm,
                    short_info=
                    ('\n\tIOPS and Throughput limits available for VM DiskType - {},'
                     '\n\tTotal DiskSize: {}:'
                     '\n\n\t Max Read-IOPS Count: {}, \n\t Max Read-Throughput: {} MB/s,'
                     '\n\t Max Write-IOPS Count: {}, \n\t Max Write-Throughput: {} MB/s\n'
                    ).format(disktype, int(total_disk_size[disktype]),
                             min(data[1], provisions_iops['pd-extreme']),
                             min(data[2], data[3]),
                             min(data[5], provisions_iops['pd-extreme']),
                             min(data[6], data[7])))

              else:
                data = limit_calculator(limits_data,
                                        mach_fam_json_data, disktype,
                                        int(total_disk_size[disktype]),
                                        search_str, next_hop, next_hop_val)
                # upto first 100GB, pd-standard disks have fixed IO limits
                if disktype == 'pd-standard' and int(
                    total_disk_size[disktype]) < 100:
                  report.add_ok(
                      vm,
                      short_info=
                      ('\n\tIOPS and Throughput limits available for VM DiskType - {},'
                       '\n\tTotal DiskSize: {}:'
                       '\n\n\t Max Read-IOPS Count: {},\n\t Max Read-Throughput: {} MB/s,'
                       '\n\t Max Write-IOPS Count: {}, \n\t Max Write-Throughput: {} MB/s \n'
                      ).format(disktype, int(total_disk_size[disktype]), 75, 12,
                               150, 12))
                else:
                  report.add_ok(
                      vm,
                      short_info=
                      ('\n\tIOPS and Throughput limits available for VM DiskType - {},'
                       '\n\tTotal DiskSize: {}:'
                       '\n\n\t Max Read-IOPS Count: {},\n\t Max Read-Throughput: {} MB/s,'
                       '\n\t Max Write-IOPS Count: {}, \n\t Max Write-Throughput: {} MB/s\n'
                      ).format(disktype, int(total_disk_size[disktype]),
                               min(data[0], data[1]), min(data[2], data[3]),
                               min(data[4], data[5]), min(data[6], data[7])))
            else:
              report.add_skipped(
                  vm,
                  reason=
                  ('The machine type {} is not supported with this gcpdiag Lint rule'
                   'You may only run this runbook for any of the below machine family:'
                   'A2, A3, C2, C2D, C3, C3D, E2, F1, G1, G2, H3, N1, N2, N2D, M1,'
                   ' M2, M3, T2D, T2A, Z3').format(vm.machine_type()))

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

                data = limit_calculator(limits_data, mach_fam_json_data,
                                        'pd-ssd',
                                        int(total_disk_size['pd-extreme']),
                                        search_str, next_hop, next_hop_val)

                report.add_ok(
                    vm,
                    short_info=
                    ('\n\tIOPS and Throughput limits available for VM DiskType - {},'
                     '\n\tTotal DiskSize: {}:'
                     '\n\n\t Max Read-IOPS Count: {}, \n\t Max Read-Throughput: {} MB/s,'
                     '\n\t Max Write-IOPS Count: {}, \n\t Max Write-Throughput: {} MB/s\n'
                    ).format(disktype, int(total_disk_size[disktype]),
                             min(data[0], provisions_iops['pd-extreme']),
                             min(data[2], data[3]),
                             min(data[4], provisions_iops['pd-extreme']),
                             min(data[6], data[7])))

              else:
                data = limit_calculator(limits_data,
                                        mach_fam_json_data, disktype,
                                        int(total_disk_size[disktype]),
                                        search_str, next_hop, next_hop_val)

                if disktype == 'pd-standard' and int(
                    total_disk_size[disktype]) < 100:
                  report.add_ok(
                      vm,
                      short_info=
                      ('\n\tIOPS and Throughput limits available for VM DiskType - {},'
                       '\n\tTotal DiskSize: {}:'
                       '\n\n\t Max Read-IOPS Count: {}, \n\t Max Read-Throughput: {} MB/s,'
                       '\n\t Max Write-IOPS Count: {}, \n\t Max Write-Throughput: {} MB/s\n'
                      ).format(disktype, int(total_disk_size[disktype]), 75, 12,
                               150, 12))
                else:
                  report.add_ok(
                      vm,
                      short_info=
                      ('\n\tIOPS and Throughput limits available for VM DiskType - {},'
                       '\n\tTotal DiskSize: {}:'
                       '\n\n\t Max Read-IOPS Count: {},\n\t Max Read-Throughput: {} MB/s,'
                       '\n\t Max Write-IOPS Count: {}, \n\t Max Write-Throughput: {} MB/s\n'
                      ).format(disktype, int(total_disk_size[disktype]),
                               min(data[0], data[1]), min(data[2], data[3]),
                               min(data[4], data[5]), min(data[6], data[7])))
            else:
              report.add_skipped(
                  vm,
                  reason=
                  ('The machine type {} is not supported with this gcpdiag Lint rule'
                   'You may only run this runbook for any of the below machine family:'
                   'A2, A3, C2, C2D, C3, C3D, E2, F1, G1, G2, H3, N1, N2, N2D, M1,'
                   ' M2, M3, T2D, T2A, Z3').format(vm.machine_type()))

          elif vm_family == 'n':
            if vm.machine_type().split('-')[0].upper() in ['N1', 'N2', 'N2D']:
              next_hop = 'VM vCPU count'
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

                data = limit_calculator(limits_data,
                                        mach_fam_json_data, disktype,
                                        int(total_disk_size[disktype]),
                                        search_str, next_hop, next_hop_val)
                report.add_ok(
                    vm,
                    short_info=
                    ('\n\tIOPS and Throughput limits available for VM DiskType - {},'
                     '\n\tTotal DiskSize: {}:'
                     '\n\n\t Max Read-IOPS Count: {}, \n\t Max Read-Throughput: {} MB/s,'
                     '\n\t Max Write-IOPS Count: {}, \n\t Max Write-Throughput: {} MB/s\n'
                    ).format(disktype, int(total_disk_size[disktype]),
                             min(data[0], data[1]), min(data[2], data[3]),
                             min(data[4], data[5]), min(data[6], data[7])))

              elif disktype == 'pd-standard':
                if cpu_count == 1:
                  next_hop_val = '1'
                elif cpu_count in range(2, 8):
                  next_hop_val = '2-7'
                elif cpu_count in range(8, 16):
                  next_hop_val = '8-15'
                elif cpu_count > 15:
                  next_hop_val = '16 or more'

                data = limit_calculator(limits_data,
                                        mach_fam_json_data, disktype,
                                        int(total_disk_size[disktype]),
                                        search_str, next_hop, next_hop_val)

                if int(total_disk_size[disktype]) < 100:
                  report.add_ok(
                      vm,
                      short_info=
                      ('\n\tIOPS and Throughput limits available for VM DiskType - {},'
                       '\n\tTotal DiskSize: {}:'
                       '\n\n\t Max Read-IOPS Count: {}, \n\t Max Read-Throughput: {} MB/s,'
                       '\n\t Max Write-IOPS Count: {}, \n\t Max Write-Throughput: {} MB/s \n'
                      ).format(disktype, int(total_disk_size[disktype]), 75, 12,
                               150, 12))
                else:
                  report.add_ok(
                      vm,
                      short_info=
                      ('\n\tIOPS and Throughput limits available for VM DiskType - {},'
                       '\n\tTotal DiskSize: {}:'
                       '\n\n\t Max Read-IOPS Count: {}, \n\t Max Read-Throughput: {} MB/s,'
                       '\n\t Max Write-IOPS Count: {}, \n\t Max Write-Throughput: {} MB/s\n'
                      ).format(disktype, int(total_disk_size[disktype]),
                               min(data[0], data[1]), min(data[2], data[3]),
                               min(data[4], data[5]), min(data[6], data[7])))

              elif disktype == 'pd-extreme':
                if search_str == 'N2 VMs' and cpu_count > 63:
                  next_hop = 'Machine type'
                  next_hop_val = vm.machine_type()
                  data = limit_calculator(limits_data, mach_fam_json_data,
                                          disktype,
                                          int(total_disk_size[disktype]),
                                          search_str, next_hop, next_hop_val)

                  report.add_ok(
                      vm,
                      short_info=
                      ('\n\tIOPS and Throughput limits available for VM DiskType - {},'
                       '\n\tTotal DiskSize: {}:'
                       '\n\n\t Max Read-IOPS Count: {}, \n\t Max Read-Throughput: {} MB/s'
                       '\n\t Max Write-IOPS Count: {}, \n\t Max Write-Throughput: {} MB/s\n'
                      ).format(disktype, int(total_disk_size[disktype]),
                               min(data[1], provisions_iops['pd-extreme']),
                               min(data[2], data[3]),
                               min(data[5], provisions_iops['pd-extreme']),
                               min(data[6], data[7])))

                else:
                  next_hop = 'VM vCPU count'
                  data = limit_calculator(limits_data, mach_fam_json_data,
                                          'pd-ssd',
                                          int(total_disk_size['pd-extreme']),
                                          search_str, next_hop, next_hop_val)
                  # https://cloud.google.com/compute/docs/disks/extreme-persistent-disk#machine_shape_support
                  report.add_ok(
                      vm,
                      short_info=
                      ('\n\tIOPS and Throughput limits available for VM DiskType - {},'
                       '\n\tTotal DiskSize: {}:'
                       '\n\n\t Max Read-IOPS Count: {}, \n\t Max Read-Throughput: {} MB/s'
                       '\n\t Max Write-IOPS Count: {}, \n\t Max Write-Throughput: {} MB/s\n'
                      ).format(disktype, int(total_disk_size[disktype]),
                               min(data[1], provisions_iops['pd-extreme']),
                               max(data[2], data[3]),
                               min(data[5], provisions_iops['pd-extreme']),
                               max(data[6], data[7])))

            else:
              report.add_skipped(
                  vm,
                  reason=
                  ('The machine type {} is not supported with this gcpdiag Lint rule'
                   'You may only run this runbook for any of the below machine family:'
                   'A2, A3, C2, C2D, C3, C3D, E2, F1, G1, G2, H3, N1, N2, N2D, M1,'
                   ' M2, M3, T2D, T2A, Z3').format(vm.machine_type()))
          else:
            report.add_skipped(
                vm,
                reason=
                ('The machine type {} is not supported with this gcpdiag Lint rule'
                 'You may only run this runbook for any of the below machine family:'
                 'A2, A3, C2, C2D, C3, C3D, E2, F1, G1, G2, H3, N1, N2, N2D, M1,'
                 ' M2, M3, T2D, T2A, Z3').format(vm.machine_type()))


def limit_calculator(limits_data, mach_fam_json_data, disktype: str,
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
