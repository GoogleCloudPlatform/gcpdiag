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
"""Vertex AI Generalized Runbook Steps"""

from gcpdiag import runbook
from gcpdiag.queries import gce, logs, monitoring, notebooks
from gcpdiag.runbook import op
from gcpdiag.runbook.gce import flags as gce_flags
from gcpdiag.runbook.gce import generalized_steps as gce_gs
from gcpdiag.runbook.vertex import constants, flags


class CheckWorkbenchInstanceCustomScripts(runbook.Step):
  """Check if the Workbench Instance is using custom scripts

  Users have the option to add scripts to a Workbench Instance
  via the metadata fields. However, scripts may change the
  default behaviour or install libraries that break dependencies
  """

  template = 'workbench_scripts::custom'
  project_id: str = ''
  instance_name: str = ''
  zone: str = ''

  def execute(self):
    """Check if the Workbench Instance has custom scripts"""
    project_id: str = self.project_id or op.get(flags.PROJECT_ID)
    instance_name: str = self.instance_name or op.get(flags.INSTANCE_NAME)
    zone: str = self.zone or op.get(flags.ZONE)
    workbench_instance: notebooks.WorkbenchInstance = notebooks.get_workbench_instance(
        project_id=project_id, zone=zone, instance_name=instance_name)
    if (workbench_instance.post_startup_script or
        workbench_instance.startup_script or
        workbench_instance.startup_script_url):
      op.add_uncertain(
          resource=workbench_instance,
          reason=op.prep_msg(
              op.UNCERTAIN_REASON,
              instance_name=instance_name,
              post_startup_script=workbench_instance.post_startup_script,
              startup_script=workbench_instance.startup_script,
              startup_script_url=workbench_instance.startup_script_url),
          remediation=op.prep_msg(op.UNCERTAIN_REMEDIATION))
    else:
      op.add_ok(resource=workbench_instance,
                reason=op.prep_msg(op.SUCCESS_REASON,
                                   instance_name=instance_name))


class CheckWorkbenchInstanceUsingOfficialImage(runbook.Step):
  """Check if the Workbench Instance is using the official images

  Users have the option to create Workbench Instances with any image
  However, only 'workbench-instances' official images are supported
  """

  template = 'workbench_images::official'
  project_id: str = ''
  instance_name: str = ''
  zone: str = ''

  def execute(self):
    """Check if Workbench Instance VM's boot disk image is one of the official images"""
    project_id: str = self.project_id or op.get(flags.PROJECT_ID)
    instance_name: str = self.instance_name or op.get(flags.INSTANCE_NAME)
    zone: str = self.zone or op.get(flags.ZONE)
    gce_instance = gce.get_instance(project_id=project_id,
                                    zone=zone,
                                    instance_name=instance_name)
    gce_instance_boot_disk_image = gce_instance.get_boot_disk_image()
    if (constants.WORKBENCH_INSTANCES_IMAGES_FAMILY
        in gce_instance_boot_disk_image and
        constants.WORKBENCH_INSTANCES_IMAGES_PROJECT
        in gce_instance_boot_disk_image):
      op.add_ok(resource=gce_instance,
                reason=op.prep_msg(
                    op.SUCCESS_REASON,
                    instance_name=instance_name,
                    image_family=constants.WORKBENCH_INSTANCES_IMAGES_FAMILY,
                    image=gce_instance_boot_disk_image))
    elif constants.DEEP_LEARNING_VM_IMAGES_PROJECT in gce_instance_boot_disk_image:
      op.add_uncertain(
          resource=gce_instance,
          reason=op.prep_msg(
              op.UNCERTAIN_REASON,
              image=gce_instance_boot_disk_image,
              images_family=constants.DEEP_LEARNING_VM_IMAGES_PROJECT),
          remediation=op.prep_msg(op.UNCERTAIN_REMEDIATION))
    else:
      op.add_failed(
          resource=gce_instance,
          reason=op.prep_msg(
              op.FAILURE_REASON,
              image=gce_instance_boot_disk_image,
              images_family=constants.WORKBENCH_INSTANCES_IMAGES_FAMILY),
          remediation=op.prep_msg(
              op.FAILURE_REMEDIATION,
              images_family=constants.WORKBENCH_INSTANCES_IMAGES_FAMILY))
      # User will need to create a new Workbench Instance


class CheckWorkbenchInstanceIsUsingLatestEnvVersion(runbook.Step):
  """Check if the Workbench Instance is using the latest environment version

  Workbench Instances can be upgraded regularly to have the latest fixes
  """

  template = 'workbench_environment_version::upgradable'
  project_id: str = ''
  instance_name: str = ''
  zone: str = ''

  def execute(self):
    """Check if the Workbench Instance is using the latest environment version"""
    project_id: str = self.project_id or op.get(flags.PROJECT_ID)
    instance_name: str = self.instance_name or op.get(flags.INSTANCE_NAME)
    zone: str = self.zone or op.get(flags.ZONE)
    workbench_instance: notebooks.WorkbenchInstance = notebooks.get_workbench_instance(
        project_id=project_id, zone=zone, instance_name=instance_name)
    workbench_instance_upgradability: dict = notebooks.workbench_instance_check_upgradability(
        project_id=project_id, workbench_instance_name=workbench_instance.name)
    workbench_instance_upgradeable: bool = workbench_instance_upgradability.get(
        'upgradeable', False)
    workbench_instance_upgrade_version: str = workbench_instance_upgradability.get(
        'upgradeVersion', '').upper()
    workbench_instance_upgrade_info: str = workbench_instance_upgradability.get(
        'upgradeInfo', '')
    workbench_instance_upgrade_image: str = workbench_instance_upgradability.get(
        'upgradeImage', '')
    op.info(f'instance is upgradeable: {workbench_instance_upgradeable}')
    op.info(f'instance upgrade info: {workbench_instance_upgrade_info}')
    if workbench_instance_upgradeable:
      op.add_failed(
          resource=workbench_instance,
          reason=op.prep_msg(
              op.FAILURE_REASON,
              instance_name=instance_name,
              environment_version=workbench_instance.environment_version),
          remediation=op.prep_msg(
              op.FAILURE_REMEDIATION,
              upgrade_version=workbench_instance_upgrade_version,
              upgrade_image=workbench_instance_upgrade_image))
    else:
      if constants.WORKBENCH_INSTANCES_UPGRADABILITY_CURRENT in workbench_instance_upgrade_info:
        op.add_ok(
            resource=workbench_instance,
            reason=op.prep_msg(
                op.SUCCESS_REASON,
                instance_name=instance_name,
                environment_version=workbench_instance.environment_version))
      elif (constants.WORKBENCH_INSTANCES_UPGRADABILITY_INVALID_STATE_INFO
            in workbench_instance_upgrade_info and
            workbench_instance.state != notebooks.StateEnum.STOPPED):
        op.add_uncertain(resource=workbench_instance,
                         reason=op.prep_msg(
                             op.UNCERTAIN_REASON,
                             instance_name=instance_name,
                             upgrade_info=workbench_instance_upgrade_info),
                         remediation=op.prep_msg(op.UNCERTAIN_REMEDIATION))
      elif not workbench_instance.environment_version:
        # Environment version is 0 and upgradability False when the instance is new
        op.add_uncertain(resource=workbench_instance,
                         reason=op.prep_msg(
                             op.UNCERTAIN_REASON_ALT1,
                             instance_name=instance_name,
                             upgrade_info=workbench_instance_upgrade_info),
                         remediation=op.prep_msg(op.UNCERTAIN_REMEDIATION_ALT1))
      else:
        op.add_uncertain(resource=workbench_instance,
                         reason=op.prep_msg(
                             op.UNCERTAIN_REASON_ALT2,
                             instance_name=instance_name,
                             upgrade_info=workbench_instance_upgrade_info),
                         remediation=op.prep_msg(op.UNCERTAIN_REMEDIATION_ALT2))


class CheckWorkbenchInstanceSyslogsJupyterRunningOnPort8080(runbook.Step):
  """Check Jupyter is running on port 127.0.0.1:8080

  Jupyter should always run on port 127.0.0.1:8080
  for the Workbench Instance to work correctly
  """

  template = 'workbench_jupyter_port::running'
  project_id: str = ''
  instance_name: str = ''
  zone: str = ''

  def execute(self):
    """Verify Jupyter is running on port 127.0.0.1:8080"""
    start_time = op.get(flags.START_TIME)
    end_time = op.get(flags.END_TIME)
    project_id: str = self.project_id or op.get(flags.PROJECT_ID)
    instance_name: str = self.instance_name or op.get(flags.INSTANCE_NAME)
    zone: str = self.zone or op.get(flags.ZONE)
    workbench_instance: notebooks.WorkbenchInstance = notebooks.get_workbench_instance(
        project_id=project_id, zone=zone, instance_name=instance_name)
    filter_str = r'''severity=INFO
                      AND
                      resource.type="gce_instance"
                      AND
                      log_name=~"projects\/{project_id}\/logs\/serialconsole.googleapis.com.*"
                      AND
                      labels."compute.googleapis.com/resource_name"="{instance_name}"
                      AND
                      textPayload=~"ServerApp.*Jupyter Server.*running at.*"'''.format(
        project_id=project_id, instance_name=instance_name)
    serial_log_entries_jupyter_running = logs.realtime_query(
        project_id=project_id,
        filter_str=filter_str,
        start_time=start_time,
        end_time=end_time)
    if serial_log_entries_jupyter_running:
      op.info(
          'Jupyter is running! Verifying if it\'s running on port 127.0.0.1:8080.'
      )
      filter_str = r'''severity=INFO
                    AND
                    resource.type="gce_instance"
                    AND
                    log_name=~"projects\/{project_id}\/logs\/serialconsole.googleapis.com.*"
                    AND
                    labels."compute.googleapis.com/resource_name"="{instance_name}"
                    AND NOT
                    textPayload=~"ServerApp.*localhost:8080\/lab"
                    AND
                    textPayload=~"ServerApp.*localhost:[0-9]{{4}}\/lab"'''.format(
          project_id=project_id, instance_name=instance_name)
      serial_log_entries_jupyter_port = logs.realtime_query(
          project_id=project_id,
          filter_str=filter_str,
          start_time=start_time,
          end_time=end_time)
      if serial_log_entries_jupyter_port:
        #User will need to fix their instance o create a new one
        op.add_failed(resource=workbench_instance,
                      reason=op.prep_msg(op.FAILURE_REASON_ALT1,
                                         instance_name=instance_name),
                      remediation=op.prep_msg(op.FAILURE_REMEDIATION))
      else:
        op.add_ok(resource=workbench_instance,
                  reason=op.prep_msg(op.SUCCESS_REASON,
                                     instance_name=instance_name))
    else:
      #User needs to make sure their instance is not stopped to get logs
      op.add_failed(resource=workbench_instance,
                    reason=op.prep_msg(op.FAILURE_REASON,
                                       instance_name=instance_name),
                    remediation=op.prep_msg(op.FAILURE_REMEDIATION))


class CheckWorkbenchInstancePerformance(runbook.CompositeStep):
  """Checks performance of a Workbench Instance by evaluating its memory, CPU, and disk utilization.

  This composite diagnostic step sequentially checks for high memory utilization, high disk
  utilization, and CPU performance issues. It adds specific child steps designed to identify
  and report potential performance bottlenecks that could impact the instance's operation.
  """

  project_id: str = ''
  instance_name: str = ''
  zone: str = ''

  def execute(self):
    """Evaluating Workbench Instance Compute Engine VM memory, CPU, and disk performance."""
    within_hours = 8
    within_str = 'within %dh, d\'%s\'' % (within_hours,
                                          monitoring.period_aligned_now(5))
    project_id: str = self.project_id or op.get(flags.PROJECT_ID)
    instance_name: str = self.instance_name or op.get(flags.INSTANCE_NAME)
    zone: str = self.zone or op.get(flags.ZONE)
    op.put(gce_flags.PROJECT_ID, project_id)
    op.put(gce_flags.NAME, instance_name)
    op.put(gce_flags.ZONE, zone)
    ops_agent_query = monitoring.query(
        op.get(flags.PROJECT_ID), """
              fetch gce_instance
              | metric 'agent.googleapis.com/agent/uptime'
              | filter (metadata.system_labels.name == '{}')
              | align rate(5m)
              | every 5m
              | {}
            """.format(op.get(gce_flags.NAME), within_str))
    if ops_agent_query:
      op.info(
          'Runbook will use ops agent metrics for VM performance investigation')

    vm_memory_utilization = gce_gs.HighVmMemoryUtilization()
    vm_memory_utilization.project_id = project_id
    vm_memory_utilization.zone = zone
    vm_memory_utilization.instance_name = instance_name

    vm_disk_utilization = gce_gs.HighVmDiskUtilization()
    vm_disk_utilization.project_id = project_id
    vm_disk_utilization.zone = zone
    vm_disk_utilization.instance_name = instance_name

    vm_cpu_utilization = gce_gs.HighVmCpuUtilization()
    vm_cpu_utilization.project_id = project_id
    vm_cpu_utilization.zone = zone
    vm_cpu_utilization.instance_name = instance_name

    self.add_child(child=vm_memory_utilization)
    self.add_child(child=vm_disk_utilization)
    self.add_child(child=vm_cpu_utilization)


class CheckWorkbenchInstanceExternalIpDisabled(runbook.Step):
  """Check if the Workbench Instance has external IP disabled

  If the instance has external IP disabled, user must configure
  Private networking correctly
  """

  template = 'workbench_ip::disabled'
  project_id: str = ''
  instance_name: str = ''
  zone: str = ''

  def execute(self):
    """Check if the Workbench Instance has external IP disabled"""
    project_id: str = self.project_id or op.get(flags.PROJECT_ID)
    instance_name: str = self.instance_name or op.get(flags.INSTANCE_NAME)
    zone: str = self.zone or op.get(flags.ZONE)
    workbench_instance: notebooks.WorkbenchInstance = notebooks.get_workbench_instance(
        project_id=project_id, zone=zone, instance_name=instance_name)
    if workbench_instance.disable_public_ip:
      op.add_uncertain(resource=workbench_instance,
                       reason=op.prep_msg(op.UNCERTAIN_REASON,
                                          instance_name=instance_name,
                                          network=workbench_instance.network,
                                          subnetwork=workbench_instance.subnet),
                       remediation=op.prep_msg(op.UNCERTAIN_REMEDIATION))
    else:
      op.add_ok(resource=workbench_instance,
                reason=op.prep_msg(op.SUCCESS_REASON,
                                   instance_name=instance_name))
