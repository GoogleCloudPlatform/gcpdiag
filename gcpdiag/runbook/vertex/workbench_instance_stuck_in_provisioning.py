#
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
"""Runbook to Troubleshoot Issue: Vertex AI Workbench Instance Stuck in Provisioning State"""
from datetime import datetime

from gcpdiag import runbook
from gcpdiag.queries import crm, gce, notebooks, orgpolicy
from gcpdiag.runbook import op
from gcpdiag.runbook.vertex import flags
from gcpdiag.runbook.vertex import generalized_steps as vertex_gs

PROVISIONING_STATES = [
    notebooks.StateEnum.PROVISIONING, notebooks.StateEnum.STARTING,
    notebooks.StateEnum.INITIALIZING
]


class WorkbenchInstanceStuckInProvisioning(runbook.DiagnosticTree):
  """Runbook to Troubleshoot Issue: Vertex AI Workbench Instance Stuck in Provisioning State

  This runbook investigates root causes for the Workbench Instance to be stuck in provisioning state

  Areas Examined:

  - Workbench Instance State: Checks the instance's current state ensuring that it is
    stuck in provisioning status and not stopped or active.

  - Workbench Instance Compute Engine VM Boot Disk Image: Checks if the instance has been created
    with a custom container, the official 'workbench-instances' images, deep learning VMs images,
    or unsupported images that might cause the instance to be stuck in provisioning state.

  - Workbench Instance Custom Scripts: Checks if the instance is not using custom scripts that may
    affect the default configuration of the instance by changing the Jupyter port or breaking
    dependencies that might cause the instance to be stuck in provisioning state.

  - Workbench Instance Environment Version: Checks if the instance is using the latest environment
    version by checking its upgradability. Old versions sometimes are the root cause for the
    instance to be stuck in provisioning state.

  - Workbench Instance Compute Engine VM Performance: Checks the VM's current performance, ensuring
    that it is not impaired by high CPU usage, insufficient memory, or disk space issues that might
    disrupt normal operations.

  - Workbench Instance Compute Engine Serial Port Logging: Checks if the instance has serial port
    logs which can be analyzed to ensure Jupyter is running on port 127.0.0.1:8080
    which is mandatory.

  - Workbench Instance Compute Engine SSH and Terminal access: Checks if the instance's
    compute engine vm is running so the user can ssh and open a terminal to check for space
    usage in 'home/jupyter'. If no space is left, that may cause the instance to be stuck
    in provisioning state.

  - Workbench Instance External IP Disabled: Checks if the external IP disabled. Wrong networking
    configurations may cause the instance to be stuck in provisioning state.
  """
  parameters = {
      flags.PROJECT_ID: {
          'type': str,
          'help': 'The Project ID of the resource under investigation',
          'required': True
      },
      flags.INSTANCE_NAME: {
          'type': str,
          'help': 'Name of the Workbench Instance',
          'default': '',
          'required': True
      },
      flags.ZONE: {
          'type': str,
          'help': 'Zone of the Workbench Instance. e.g. us-central1-a',
          'default': 'us-central1-a',
          'required': True
      },
      flags.START_TIME_UTC: {
          'type': datetime,
          'help': 'Start time of the issue',
      },
      flags.END_TIME_UTC: {
          'type': datetime,
          'help': 'End time of the issue',
      }
  }

  def build_tree(self):
    """Desribes step relationships"""
    start = WorkbenchInstanceStuckInProvisioningStart()
    check_custom_container = CheckWorkbenchInstanceUsingCustomContainer()
    check_workbench_instance_image = vertex_gs.CheckWorkbenchInstanceUsingOfficialImage(
    )
    check_workbench_instance_custom_scripts = vertex_gs.CheckWorkbenchInstanceCustomScripts(
    )
    check_workbench_instance_version = vertex_gs.CheckWorkbenchInstanceIsUsingLatestEnvVersion(
    )
    check_workbench_instance_performance = vertex_gs.CheckWorkbenchInstancePerformance(
    )
    check_workbench_instance_logging = DecisionCheckWorkbenchInstanceSystemLogging(
    )
    check_workbench_instance_compute_vm_ssh = CheckWorkbenchInstanceComputeEngineSSH(
    )
    check_workbench_instance_ip_disabled = vertex_gs.CheckWorkbenchInstanceExternalIpDisabled(
    )
    self.add_start(start)
    self.add_step(parent=start, child=check_custom_container)
    self.add_step(parent=check_custom_container,
                  child=check_workbench_instance_image)
    self.add_step(parent=check_workbench_instance_image,
                  child=check_workbench_instance_custom_scripts)
    self.add_step(parent=check_workbench_instance_custom_scripts,
                  child=check_workbench_instance_version)
    self.add_step(parent=check_workbench_instance_version,
                  child=check_workbench_instance_performance)
    self.add_step(parent=check_workbench_instance_version,
                  child=check_workbench_instance_logging)
    self.add_step(parent=check_workbench_instance_version,
                  child=check_workbench_instance_compute_vm_ssh)
    self.add_step(parent=check_workbench_instance_version,
                  child=check_workbench_instance_ip_disabled)
    self.add_end(WorkbenchInstanceStuckInProvisioningEnd())


class WorkbenchInstanceStuckInProvisioningStart(runbook.StartStep):
  """Checking if the Workbench Instance is in PROVISIONING state and gathering its details...

  If the instance is stopped, user must try to start it to start the checks
  """

  template = 'workbench_state::provisioning_stuck'

  def execute(self):
    """Sets values to be used and get resources from Notebooks and GCE APIs"""
    # === Get parameters and project information ===
    project: str = crm.get_project(op.get(flags.PROJECT_ID))
    if project:
      op.info(f'project id: {project.id}, project number: {project.number}')
    product: str = self.__module__.split('.')[-2]
    op.info(f'product: {product} workbench instances')
    instance_name: str = op.get(flags.INSTANCE_NAME)
    op.info(f'instance name parameter: {instance_name}')
    zone: str = op.get(flags.ZONE)
    op.info(f'instance zone parameter: {zone}')
    op.info('--- Workbench Instance ---')
    workbench_instance: notebooks.WorkbenchInstance = notebooks.get_workbench_instance(
        project_id=project.id, zone=zone, instance_name=instance_name)
    gce_instance: gce.Instance = gce.get_instance(project_id=project.id,
                                                  zone=zone,
                                                  instance_name=instance_name)
    self.print_workbench_instance_data(workbench_instance=workbench_instance)
    op.info(f'instance compute engine vm name: {gce_instance.name}')
    op.info(f'instance compute engine vm is running: {gce_instance.is_running}')
    workbench_instance_upgradability: dict = notebooks.workbench_instance_check_upgradability(
        project_id=project.id, workbench_instance_name=workbench_instance.name)
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
      op.info(f'instance upgrade version: {workbench_instance_upgrade_version}')
      op.info(f'instance upgrade image: {workbench_instance_upgrade_image}')
    if workbench_instance.report_event_health:
      op.info('--- Workbench Instance Health State ---')
      self.print_workbench_instance_health_data(
          workbench_instance=workbench_instance)
    op.info(f'instance state: {workbench_instance.state}')

    if workbench_instance.state == notebooks.StateEnum.ACTIVE:
      op.add_ok(resource=workbench_instance,
                reason=op.prep_msg(op.SUCCESS_REASON,
                                   instance_name=instance_name))
    elif workbench_instance.state not in PROVISIONING_STATES:
      op.add_failed(resource=workbench_instance,
                    reason=op.prep_msg(op.FAILURE_REASON,
                                       instance_name=instance_name),
                    remediation=op.prep_msg(op.FAILURE_REMEDIATION))
    else:
      op.add_ok(resource=workbench_instance,
                reason=op.prep_msg(op.SUCCESS_REASON_ALT1,
                                   instance_name=instance_name))

  def print_workbench_instance_data(
      self, workbench_instance: notebooks.WorkbenchInstance):
    op.info(f'instance name: {workbench_instance.name}')
    op.info(f'instance state: {workbench_instance.state}')
    op.info(
        f'instance environment version: {workbench_instance.environment_version}'
    )
    op.info(
        f'instance compute account: {workbench_instance.gce_service_account_email}'
    )
    op.info(f'instance network: {workbench_instance.network}')
    op.info(f'instance subnetwork: {workbench_instance.subnet}')
    op.info(
        f'instance public ip disabled: {workbench_instance.disable_public_ip}')
    op.info(
        f'instance metadata disable-mixer: {workbench_instance.disable_mixer}')
    op.info('instance metadata serial-port-logging-enable:'
            f'{workbench_instance.serial_port_logging_enabled}')
    op.info(
        f'instance metadata post-startup-script: {workbench_instance.post_startup_script}'
    )
    op.info(
        f'instance metadata startup-script: {workbench_instance.startup_script}'
    )
    op.info(
        f'instance metadata startup-script-url: {workbench_instance.startup_script_url}'
    )
    op.info(
        f'instance metadata report-event-health: {workbench_instance.report_event_health}'
    )

  def print_workbench_instance_health_data(
      self, workbench_instance: notebooks.WorkbenchInstance):
    op.info(f'instance health - state: {workbench_instance.health_state}')
    op.info('instance health - jupyterlab status healthy:'
            f'{workbench_instance.is_jupyterlab_status_healthy}')
    op.info('instance health - jupyterlab api status healthy:'
            f'{workbench_instance.is_jupyterlab_api_status_healthy}')
    op.info('instance health - notebooks api dns healthy:'
            f'{workbench_instance.is_notebooks_api_dns_healthy}')
    op.info('instance health - proxy registration dns healthy:'
            f'{workbench_instance.is_proxy_registration_dns_healthy}')
    op.info('instance health - system healthy:'
            f'{workbench_instance.is_system_healthy}')
    op.info('instance health - docker status healthy:'
            f'{workbench_instance.is_docker_status_healthy}')


class CheckWorkbenchInstanceUsingCustomContainer(runbook.Step):
  """Check if the Workbench Instance is using a custom container

  Users have the option to use custom containers to create Workbench Instances
  If this is the case, this runbook doesn't apply
  """

  template = 'workbench_container::custom'

  def execute(self):
    """Checking if the Workbench Instance is using a custom container..."""
    project_id: str = op.get(flags.PROJECT_ID)
    instance_name: str = op.get(flags.INSTANCE_NAME)
    zone: str = op.get(flags.ZONE)
    workbench_instance: notebooks.WorkbenchInstance = notebooks.get_workbench_instance(
        project_id=project_id, zone=zone, instance_name=instance_name)
    response = op.prompt(
        kind=op.CONFIRMATION,
        message='Is your Workbench Instance using a custom container?')
    if response == op.YES:
      op.add_uncertain(resource=workbench_instance,
                       reason=op.prep_msg(op.UNCERTAIN_REASON),
                       remediation=op.prep_msg(op.UNCERTAIN_REMEDIATION))
    else:
      op.add_ok(resource=workbench_instance,
                reason=op.prep_msg(op.SUCCESS_REASON,
                                   instance_name=instance_name))


class DecisionCheckWorkbenchInstanceSystemLogging(runbook.Gateway):
  """Decision point to investigate Serial Port Logs

  Decides whether its possible to check syslogs for the
  Workbench Instance
  """

  template = 'workbench_system_logs::enabled'

  def execute(self):
    """Decision point to investigate Serial Port Logs"""
    project_id = op.get(flags.PROJECT_ID)
    instance_name: str = op.get(flags.INSTANCE_NAME)
    zone: str = op.get(flags.ZONE)
    workbench_instance: notebooks.WorkbenchInstance = notebooks.get_workbench_instance(
        project_id=project_id, zone=zone, instance_name=instance_name)
    constraint_name: str = 'constraints/compute.disableSerialPortLogging'
    constraint = orgpolicy.get_effective_org_policy(project_id, constraint_name)
    metadata_name = 'serial-port-logging-enabled'
    if constraint.is_enforced():
      op.add_uncertain(resource=workbench_instance,
                       reason=op.prep_msg(op.UNCERTAIN_REASON,
                                          instance_name=instance_name,
                                          constraint=constraint_name),
                       remediation=op.prep_msg(op.UNCERTAIN_REMEDIATION,
                                               constraint=constraint_name))
    elif not workbench_instance.serial_port_logging_enabled:
      op.add_uncertain(
          resource=workbench_instance,
          reason=op.prep_msg(
              op.UNCERTAIN_REASON_ALT1,
              instance_name=instance_name,
              metadata=metadata_name,
              metadata_value=workbench_instance.serial_port_logging_enabled),
          remediation=op.prep_msg(op.UNCERTAIN_REMEDIATION_ALT1,
                                  metadata=metadata_name))
    elif (workbench_instance.state not in PROVISIONING_STATES and
          workbench_instance != notebooks.StateEnum.ACTIVE):
      op.add_uncertain(resource=workbench_instance,
                       reason=op.prep_msg(op.UNCERTAIN_REASON_ALT2,
                                          instance_name=instance_name,
                                          state=workbench_instance.state),
                       remediation=op.prep_msg(op.UNCERTAIN_REMEDIATION_ALT2))
    else:
      self.add_child(
          vertex_gs.CheckWorkbenchInstanceSyslogsJupyterRunningOnPort8080())
      op.add_ok(resource=workbench_instance,
                reason=op.prep_msg(op.SUCCESS_REASON,
                                   instance_name=instance_name))


class CheckWorkbenchInstanceComputeEngineSSH(runbook.CompositeStep):
  """Check if user is able to SSH to the Workbench Instance Compute Engine VM

  Compute Engine might be running so the user can ssh to
  inspect the VM
  """

  template = 'workbench_compute::ssh'

  def execute(self):
    """Check if user is able to SSH to the Workbench Instance Compute Engine VM"""
    #TO-DO change this to use the GCE SSH runbook or steps
    project_id = op.get(flags.PROJECT_ID)
    instance_name: str = op.get(flags.INSTANCE_NAME)
    zone: str = op.get(flags.ZONE)
    gce_instance: gce.Instance = gce.get_instance(project_id=project_id,
                                                  zone=zone,
                                                  instance_name=instance_name)
    if not gce_instance.is_running:
      op.add_uncertain(resource=gce_instance,
                       reason=op.prep_msg(op.UNCERTAIN_REASON,
                                          instance_name=instance_name,
                                          status=gce_instance.status),
                       remediation=op.prep_msg(op.UNCERTAIN_REMEDIATION))
    else:
      op.info('Workbench Instance Compute Engine VM is Running!')
      response = op.prompt(
          kind=op.CONFIRMATION,
          message=
          ('Try to SSH to the instance via Compute Engine and open a terminal. '
           'Are you able to SSH and open a terminal?'))
      if response == op.NO:
        op.add_uncertain(resource=gce_instance,
                         reason=op.prep_msg(op.UNCERTAIN_REASON_ALT1,
                                            instance_name=instance_name),
                         remediation=op.prep_msg(op.UNCERTAIN_REMEDIATION_ALT1))
      else:
        self.add_child(CheckWorkbenchInstanceJupyterSpace())
        op.add_ok(resource=gce_instance,
                  reason=op.prep_msg(op.SUCCESS_REASON,
                                     instance_name=instance_name))


class CheckWorkbenchInstanceJupyterSpace(runbook.Step):
  """Check if Jupyter space in "home/jupyter" is below 85%

  If Jupyter has ran out of space, the Workbench Instance
  might not be able to start
  """

  template = 'workbench_jupyter_space::available'

  def execute(self):
    """Check if Jupyter space in "home/jupyter" is below 85%"""
    project_id = op.get(flags.PROJECT_ID)
    instance_name: str = op.get(flags.INSTANCE_NAME)
    zone: str = op.get(flags.ZONE)
    gce_instance: gce.Instance = gce.get_instance(project_id=project_id,
                                                  zone=zone,
                                                  instance_name=instance_name)
    op.info('In the Workbench Instance Compute Engine VM terminal run "df". '
            'Verify "home/jupyter" used space is below 85%')
    response = op.prompt(kind=op.CONFIRMATION,
                         message='Is "home/jupyter" space usage more than 85%?')
    if response == op.YES:
      op.add_failed(resource=gce_instance,
                    reason=op.prep_msg(op.FAILURE_REASON,
                                       instance_name=instance_name),
                    remediation=op.prep_msg(op.FAILURE_REMEDIATION))
    else:
      op.add_ok(resource=gce_instance,
                reason=op.prep_msg(op.SUCCESS_REASON,
                                   instance_name=instance_name))


class WorkbenchInstanceStuckInProvisioningEnd(runbook.EndStep):
  """Checking if the Workbench Instance is now in ACTIVE state...

  If Workbench Instance is still stuck in PROVISIONING state, then
  Diagnostic Logs should be captured and analyzed by the user or support
  """

  template = 'workbench_state::provisioning_stuck'

  def execute(self):
    """Check if the instance is now in ACTIVE state"""
    project_id: str = op.get(flags.PROJECT_ID)
    instance_name: str = op.get(flags.INSTANCE_NAME)
    zone: str = op.get(flags.ZONE)
    workbench_instance: notebooks.WorkbenchInstance = notebooks.get_workbench_instance(
        project_id=project_id, zone=zone, instance_name=instance_name)
    op.info(f'instance state: {workbench_instance.state}')
    if workbench_instance.state == notebooks.StateEnum.ACTIVE:
      op.add_ok(resource=workbench_instance,
                reason=op.prep_msg(op.SUCCESS_REASON_ALT2,
                                   instance_name=instance_name))
    elif workbench_instance.state not in PROVISIONING_STATES:
      op.add_uncertain(resource=workbench_instance,
                       reason=op.prep_msg(op.UNCERTAIN_REASON,
                                          instance_name=instance_name),
                       remediation=op.prep_msg(op.UNCERTAIN_REMEDIATION))
    else:
      op.add_failed(resource=workbench_instance,
                    reason=op.prep_msg(op.FAILURE_REASON_ALT1,
                                       instance_name=instance_name),
                    remediation=op.prep_msg(op.FAILURE_REMEDIATION_ALT1))
      op.info(message=op.END_MESSAGE)
