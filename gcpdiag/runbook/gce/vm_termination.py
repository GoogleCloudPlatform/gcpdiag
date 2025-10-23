#
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
"""Module containing VM Termination diagnostic tree and custom steps"""

import re
from datetime import datetime

import googleapiclient.errors
from boltons.iterutils import get_path
from dateutil import parser

from gcpdiag import runbook, utils
from gcpdiag.queries import crm, gce, logs
from gcpdiag.runbook import exceptions as runbook_exceptions
from gcpdiag.runbook import op
from gcpdiag.runbook.gce import constants, flags
from gcpdiag.runbook.gce import util as gce_util

TERMINATION_OPERATION_FILTER = '''(targetId = "{INSTANCE_ID}") AND
    (operationType = "compute.instances.repair.recreateInstance") OR
    (operationType = "compute.instances.hostError") OR
    (operationType = "compute.instances.guestTerminate") OR
    (operationType = "compute.instances.preempted") OR
    (operationType = "compute.instances.terminateOnHostMaintenance") OR
    (operationType = "stop") OR
    (operationType = "compute.instanceGroupManagers.resizeAdvanced") OR
    (operationType = "compute.autoscalers.resize")
    '''


class VmTermination(runbook.DiagnosticTree):
  """GCE Instance unexpected shutdowns and reboots diagnostics

  This runbook assists in investigating and understanding the reasons behind unexpected
  terminations or reboots of GCE Virtual Machines (VMs).

  Areas investigated:

  - System event-triggered shutdowns and reboots: Identifies terminations initiated by Google Cloud
    systems due to maintenance events, hardware failures, or resource constraints.

  - Admin activities-triggered shutdown/reboot: Investigates terminations caused by direct actions,
    such as API calls made by users or service accounts, including manual shutdowns, restarts, or
    automated processes impacting VM states.
  """
  parameters = {
      flags.PROJECT_ID: {
          'type': str,
          'help': 'The Project ID hosting the terminated VM.',
          'required': True
      },
      flags.INSTANCE_NAME: {
          'type':
              str,
          'help':
              'The name of the terminated VM. Or provide the id i.e -p id=<int>',
          'required':
              True
      },
      flags.INSTANCE_ID: {
          'type':
              int,
          'help':
              'The instance ID of the terminated VM. Or provide name instead i.e -p name=<str>'
      },
      flags.ZONE: {
          'type': str,
          'help': 'The Google Cloud zone where the terminated VM is located.',
          'required': True
      },
      flags.START_TIME: {
          'type':
              datetime,
          'help':
              'The start window to investigate vm termination. Format: YYYY-MM-DDTHH:MM:SSZ'
      },
      flags.END_TIME: {
          'type':
              datetime,
          'help':
              'The end window for the investigation. Format: YYYY-MM-DDTHH:MM:SSZ'
      },
      flags.OPERATION_TYPE: {
          'type':
              str,
          'help':
              'The type of operation to investigate. eg. "compute.instances.hostError"',
      }
  }

  def build_tree(self):
    """Composes the VM runbook tree"""
    start = VmTerminationStart()
    self.add_start(start)
    self.add_step(parent=start, child=TerminationOperationType())
    self.add_end(VmTerminationEnd())


class VmTerminationStart(runbook.StartStep):
  """VM termination pre-runbook checks"""

  def execute(self):
    """Validate the provided parameters to investigate VM terminations."""
    project = crm.get_project(op.get(flags.PROJECT_ID))
    op.put(flags.PROJECT_NUMBER, project.number)
    vm = None
    try:
      name = op.get(flags.INSTANCE_NAME) or op.get(flags.INSTANCE_ID)
      vm = gce.get_instance(project_id=op.get(flags.PROJECT_ID),
                            zone=op.get(flags.ZONE),
                            instance_name=name)
    except (googleapiclient.errors.HttpError, KeyError):
      op.add_skipped(
          project,
          reason=('Instance {} does not exist in zone {} or project {}').format(
              name, op.get(flags.ZONE), op.get(flags.PROJECT_ID)))
    else:
      if vm and name.isdigit():
        op.put(flags.INSTANCE_NAME, vm.name)
      elif vm and not name.isdigit():
        op.put(flags.INSTANCE_ID, vm.id)

    # Improvements: output details of the VM as op.info


def is_within_window(operation, start_time, end_time):
  """Check if the operation is within the given time window"""
  operation_time = parser.parse(operation['startTime'])
  return start_time <= operation_time <= end_time


class TerminationOperationType(runbook.Gateway):
  """Determine the type of termination

  Analyzes log entries to identify whether the termination was normal or abnormal
  from a guest OS perspective. Was the shutdown intentionally issued by a user or a system fault?
  """

  def execute(self):
    """Investigate VM termination reason."""
    project = crm.get_project(op.get(flags.PROJECT_ID))
    try:
      gce_util.ensure_instance_resolved()
    except (runbook_exceptions.FailedStepError,
            runbook_exceptions.MissingParameterError) as e:
      op.add_skipped(project, reason=str(e))
      return

    instance_id = op.get(flags.INSTANCE_ID)
    operation_type = op.get(flags.OPERATION_TYPE)
    filter_str = (
        f'(targetId = "{instance_id}") AND (operationType = "{operation_type}")'
        if operation_type else TERMINATION_OPERATION_FILTER.format(
            INSTANCE_ID=instance_id))

    res = gce.get_global_operations(
        project=op.get(flags.PROJECT_ID),
        filter_str=filter_str,
        service_project_number=project.number,
        order_by='creationTimestamp desc',
        max_results=5,
    )

    start = op.get(flags.START_TIME)
    end = op.get(flags.END_TIME)

    operations = list(filter(lambda o: is_within_window(o, start, end), res))
    if operations:
      # get the most recent termination operation
      operation_type = get_path(operations[0], ('operationType'))
      progress = get_path(operations[0], ('progress'))
      # if part of a mig
      if progress == 100 and operation_type == constants.IG_INSTANCE_REPAIR_METHOD:
        mig_recreation = ManagedInstanceGroupRecreation()
        mig_recreation.status = get_path(operations[0], ('statusMessage'))
        self.add_child(mig_recreation)
      elif progress == 100 and operation_type == constants.INSTANCE_PREMPTION_METHOD:
        preemptible_instance_termination = PreemptibleInstance()
        preemptible_instance_termination.status = get_path(
            operations[0], ('statusMessage'))
        self.add_child(preemptible_instance_termination)
      elif progress == 100 and operation_type == constants.HOST_ERROR_METHOD:
        host_error = HostError()
        host_error.status = get_path(operations[0], ('statusMessage'))
        self.add_child(host_error)
      elif progress == 100 and operation_type == constants.GUEST_TERMINATE_METHOD:
        # Coverage: Differentiate between user and system initiated shutdowns. eg: shutdown due
        # to integrity monitoring https://cloud.google.com/compute/shielded-vm/docs/
        # integrity-monitoring#updating-baseline
        # Help users to understand the PCRs and how to fix it
        guest_os_issued_shutdown = GuestOsIssuedShutdown()
        guest_os_issued_shutdown.status = get_path(operations[0],
                                                   ('statusMessage'))
        self.add_child(guest_os_issued_shutdown)
      elif progress == 100 and operation_type == constants.TERMINATE_ON_HOST_MAINTENANCE_METHOD:
        terminate_on_host_maintenance = TerminateOnHostMaintenance()
        terminate_on_host_maintenance.status = get_path(operations[0],
                                                        ('statusMessage'))
        self.add_child(terminate_on_host_maintenance)
      elif progress == 100 and operation_type == 'stop':
        stop_gateway = StopOperationGateway()
        stop_gateway.stop_account = get_path(operations[0], ('user'))
        stop_gateway.operation_name = get_path(operations[0], ('name'))
        self.add_child(stop_gateway)


class ManagedInstanceGroupRecreation(runbook.Step):
  """Investigate if an instance recreation by MIG was normal

  Determines if the instance was recreated as part of a normal Managed Instance Group (MIG) process.
  """
  template = 'vm_termination::mig_instance_recreation'

  def execute(self):
    """Investigate if instance was recreated by a MIG"""
    vm = gce.get_instance(project_id=op.get(flags.PROJECT_ID),
                          zone=op.get(flags.ZONE),
                          instance_name=op.get(flags.INSTANCE_NAME))
    reason = op.prep_msg(op.FAILURE_REASON,
                         full_resource_path=vm.full_path,
                         status_message=self.status)
    remediation = 'No action required.'
    try:
      if vm.created_by_mig and vm.mig.version_target_reached:
        remediation = op.prep_msg(op.FAILURE_REMEDIATION,
                                  full_resource_path=vm.full_path)
      elif vm.created_by_mig and not vm.mig.version_target_reached:
        # Coverage: Give more insights into what is preventing the instance from being recreated
        remediation = op.prep_msg(op.FAILURE_REMEDIATION_ALT1,
                                  full_resource_path=vm.full_path)
    except AttributeError:
      pass
    op.add_failed(resource=vm, reason=reason, remediation=remediation)


class PreemptibleInstance(runbook.Step):
  """Investigate the cause of a preemptible VM termination

  Preemptible VMs are short-lived instances. This step investigates normal or abnormal
  circumstances leading to termination.
  """
  template = 'vm_termination::preemptible_instance'

  def execute(self):
    """Investigate the cause of a Spot VM termination"""
    try:
      vm = gce.get_instance(project_id=op.get(flags.PROJECT_ID),
                            zone=op.get(flags.ZONE),
                            instance_name=op.get(flags.INSTANCE_NAME))
    except googleapiclient.errors.HttpError:
      op.add_skipped(resource=None, reason='Spot Instance has been deleted.')
    else:
      if vm.is_preemptible_vm and vm.is_running:
        op.add_failed(resource=vm,
                      reason=op.prep_msg(op.FAILURE_REASON,
                                         full_resource_path=vm.full_path,
                                         status_message=self.status),
                      remediation=op.prep_msg(op.FAILURE_REMEDIATION,
                                              full_resource_path=vm.full_path))
      elif vm.is_preemptible_vm and not vm.is_running:
        op.add_failed(resource=vm,
                      reason=op.prep_msg(op.FAILURE_REASON,
                                         full_resource_path=vm.full_path,
                                         status_message=self.status),
                      remediation=op.prep_msg(op.FAILURE_REMEDIATION_ALT1,
                                              full_resource_path=vm.full_path))


class HostError(runbook.Step):
  """Investigate the cause of a host error

  Host errors should be rare. This step provides insights into the root cause of the issue.
  """
  template = 'vm_termination::host_error'

  def execute(self):
    """Investigate the cause of a host error"""
    vm = gce.get_instance(project_id=op.get(flags.PROJECT_ID),
                          zone=op.get(flags.ZONE),
                          instance_name=op.get(flags.INSTANCE_NAME))
    op.add_failed(resource=vm,
                  reason=op.prep_msg(op.FAILURE_REASON,
                                     full_resource_path=vm.full_path,
                                     status_message=self.status),
                  remediation=op.prep_msg(op.FAILURE_REMEDIATION,
                                          full_resource_path=vm.full_path))


class GuestOsIssuedShutdown(runbook.Step):
  """Investigate shutdowns issued from within the guest OS

  This step investigates whether the VM termination was initiated by a user or a system fault
  within the guest OS. It provides insights into the root cause of the termination.
  """
  template = 'vm_termination::guest_os_issued_shutdown'

  def execute(self):
    """Investigate the cause of a guest OS issued shutdown"""
    vm = gce.get_instance(project_id=op.get(flags.PROJECT_ID),
                          zone=op.get(flags.ZONE),
                          instance_name=op.get(flags.INSTANCE_NAME))
    # Coverage: analyze the serial port logs to provide more insights into the termination

    op.add_failed(resource=vm,
                  reason=op.prep_msg(op.FAILURE_REASON,
                                     full_resource_path=vm.full_path,
                                     status_message=self.status),
                  remediation=op.prep_msg(op.FAILURE_REMEDIATION,
                                          full_resource_path=vm.full_path))


class TerminateOnHostMaintenance(runbook.Step):
  """Investigate the cause of termination related to host maintenance

  Termination on host maintenance is normal behavior. This step verifies if it was expected.
  This will typically happen during a failed live migration.
  """
  template = 'vm_termination::terminate_on_host_maintenance'
  status: str

  def execute(self):
    """Investigate the cause of termination on host maintenance"""
    vm = gce.get_instance(project_id=op.get(flags.PROJECT_ID),
                          zone=op.get(flags.ZONE),
                          instance_name=op.get(flags.INSTANCE_NAME))
    op.add_failed(resource=vm,
                  reason=op.prep_msg(op.FAILURE_REASON,
                                     full_resource_path=vm.full_path,
                                     status_message=self.status),
                  remediation=op.prep_msg(op.FAILURE_REMEDIATION,
                                          full_resource_path=vm.full_path))


class UserOrServiceAccountInitiatedStop(runbook.Step):
  """Investigate the cause of a user-initiated VM termination

  This step investigates whether the VM termination was initiated by a user or a system fault.
  """
  template = 'vm_termination::user_stop'
  stop_account: str

  def execute(self):
    """Investigate the cause of a user-initiated VM termination"""
    vm = gce.get_instance(project_id=op.get(flags.PROJECT_ID),
                          zone=op.get(flags.ZONE),
                          instance_name=op.get(flags.INSTANCE_NAME))

    if not vm.is_running:
      op.add_failed(resource=vm,
                    reason=op.prep_msg(op.FAILURE_REASON,
                                       full_resource_path=vm.full_path,
                                       stop_account=self.stop_account),
                    remediation=op.prep_msg(op.FAILURE_REMEDIATION,
                                            full_resource_path=vm.full_path,
                                            stop_account=self.stop_account))
    else:
      op.add_failed(resource=vm,
                    reason=op.prep_msg(op.FAILURE_REASON,
                                       full_resource_path=vm.full_path,
                                       stop_account=self.stop_account),
                    remediation=op.prep_msg(op.FAILURE_REMEDIATION_ALT1,
                                            full_resource_path=vm.full_path,
                                            stop_account=self.stop_account))


class ComputeClusterManagerTermination(runbook.Step):
  """Investigate termination initiated by GCP GCE Compute Cluster Manager

  Google's Compute Cluster Manager can terminate instances due to billing issues or other reasons.
  This step investigates the root cause of the termination.
  """
  template = 'vm_termination::compute_cluster_manager_termination'
  stop_account: str

  def execute(self):
    """Investigate termination initiated by Google's Compute Cluster Manager"""
    vm = gce.get_instance(project_id=op.get(flags.PROJECT_ID),
                          zone=op.get(flags.ZONE),
                          instance_name=op.get(flags.INSTANCE_NAME))

    vpc_project = 'Unknown'
    network_name = 'Unknown'
    # try to get more infomratino about the what happened
    try:
      network_string = vm.get_network_interfaces[0]['network']
      m = re.match(r'^.+/projects/([^/]+)/global/networks/([^/]+)$',
                   network_string)
      if m:
        vpc_project, network_name = m.group(1), m.group(2)

    except googleapiclient.errors.HttpError as e:
      err = utils.GcpApiError(e)
      m = re.search(r'projects\/([^\/]+)', str(err.response))
      if m:
        vpc_project = m.group(1)
    if vpc_project != op.get(flags.PROJECT_ID):
      op.add_failed(resource=vm,
                    reason=op.prep_msg(op.FAILURE_REASON,
                                       full_resource_path=vm.full_path,
                                       stop_account=self.stop_account),
                    remediation=op.prep_msg(op.FAILURE_REMEDIATION_ALT1,
                                            full_resource_path=vm.full_path,
                                            network_name=network_name,
                                            shared_vpc_project=vpc_project,
                                            stop_account=self.stop_account))


class StopOperationGateway(runbook.Gateway):
  """Determine the kind of stop operation

  Stop operations can be caused by a user, customer-owned service account, or Google workflows
  due to billing issues or resource policies.
  """
  stop_account: str
  operation_name: str

  def execute(self):
    """Decision point to investigate various stop operation types"""
    # Termination due to scheduled policy
    compute_sa = f'service-{op.get(flags.PROJECT_NUMBER)}@compute-system.iam.gserviceaccount.com'
    if self.stop_account == compute_sa:
      log_entries = logs.realtime_query(
          project_id=op.get(flags.PROJECT_ID),
          filter_str=f'''resource.labels.instance_id="{op.get(flags.INSTANCE_ID)}"
        operation.id="{self.operation_name}"
        ''',
          start_time=op.get(flags.START_TIME),
          end_time=op.get(flags.END_TIME))
      if log_entries:
        for log_entry in log_entries:
          if get_path(log_entry,
                      ('protoPayload', 'methodName')) == 'ScheduledVMs':
            scheduled_stop_policy = ScheduledStopPolicy()
            scheduled_stop_policy.stop_account = self.stop_account
            self.add_child(scheduled_stop_policy)
            return
    elif self.stop_account != constants.GCE_CLUSTER_MANAGER_EMAIL:
      user_stop = UserOrServiceAccountInitiatedStop()
      user_stop.stop_account = self.stop_account
      self.add_child(user_stop)
    elif self.stop_account == constants.GCE_CLUSTER_MANAGER_EMAIL:
      compute_cluster_manager_termination = ComputeClusterManagerTermination()
      compute_cluster_manager_termination.stop_account = self.stop_account
      self.add_child(compute_cluster_manager_termination)


class ScheduledStopPolicy(runbook.Step):
  """Investigate the cause of a scheduled stop policy

  This step investigates whether the VM termination was initiated by a scheduled stop policy.
  """
  template = 'vm_termination::scheduled_stop_policy'
  stop_account: str

  def execute(self):
    """Investigate the scheduled stop policy"""
    vm = gce.get_instance(project_id=op.get(flags.PROJECT_ID),
                          zone=op.get(flags.ZONE),
                          instance_name=op.get(flags.INSTANCE_NAME))

    if vm.is_running:
      op.add_failed(resource=vm,
                    reason=op.prep_msg(op.FAILURE_REASON,
                                       full_resource_path=vm.full_path,
                                       stop_account=self.stop_account),
                    remediation=op.prep_msg(op.FAILURE_REMEDIATION,
                                            full_resource_path=vm.full_path,
                                            stop_account=self.stop_account))
    else:
      op.add_failed(resource=vm,
                    reason=op.prep_msg(op.FAILURE_REASON,
                                       full_resource_path=vm.full_path,
                                       stop_account=self.stop_account),
                    remediation=op.prep_msg(op.FAILURE_REMEDIATION_ALT1,
                                            full_resource_path=vm.full_path,
                                            stop_account=self.stop_account))


class VmTerminationEnd(runbook.EndStep):
  """Finalize the diagnostics process for VM terminations

  This step prompts the user to confirm satisfaction with the Root Cause Analysis (RCA) performed
  for VM terminations. Depending on the user's response, it may conclude the runbook execution
  or trigger additional steps, such as generating a report of the findings.
  """

  def execute(self):
    """Finalize VM terminations diagnostics."""
    response = op.prompt(
        kind=op.CONFIRMATION,
        message='Are you satisfied with the VM termination RCA performed?')
    if response == op.NO:
      op.info(message=op.END_MESSAGE)
      op.interface.rm.generate_report()
