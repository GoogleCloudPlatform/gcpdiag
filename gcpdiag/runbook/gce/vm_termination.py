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

from datetime import datetime
from typing import Dict

import googleapiclient.errors
from boltons.iterutils import get_path

from gcpdiag import runbook
from gcpdiag.models import Resource
from gcpdiag.queries import crm, gce, logs
from gcpdiag.runbook import op
from gcpdiag.runbook.gce import flags
from gcpdiag.runbook.gcp import generalized_steps as gcp_gs

SCOPE_TO_SINGLE_VM = 'vm_exists'

LOGGING_FILTER = '''resource.type="gce_instance"
  protoPayload.methodName=~"compute.instances.(hostError|guestTerminate|preempted|terminateOnHostMaintenance|stop|suspend|repair.recreateInstance)" OR
  protoPayload.methodName=~"compute.(instanceGroupManagers.resizeAdvanced|autoscalers.resize)"
  log_id("cloudaudit.googleapis.com/system_event") OR
  log_id("cloudaudit.googleapis.com/activity")
  '''


class VmTermination(runbook.DiagnosticTree):
  """GCE VM shutdowns and reboots Root Cause Analysis (RCA)

  This runbook is designed to assist you in investigating and understanding the underlying reasons
  behind the unexpected termination or reboot of your GCE Virtual Machines (VMs) within Google
  Cloud Platform.

  Key Investigation Areas:

  System Event-Triggered Shutdowns/Reboots: Identifies terminations initiated by internal Google
  Cloud systems due to system maintenance events, normal hardware failures,
  resource constraints.

  System Admin Activities-Triggered Shutdowns/Reboots: Investigates terminations caused by
  direct actions, such as API calls made by users or service accounts. These actions
  may include manual shutdowns, restarts, or automated processes impacting VM states.

  RCA Text Generation: Provides a detailed Root Cause Analysis text, outlining the identified
  cause of termination, the involved systems or activities, and recommendations
  to prevent future occurrences where applicable.
  """
  parameters = {
      flags.PROJECT_ID: {
          'type': str,
          'help': (
              'The Project ID associated with the terminated VM.'
              'For investigations covering multiple VMs, provide only the Project ID.'
          ),
          'required': True
      },
      flags.NAME: {
          'type':
              str,
          'help':
              'The name of the terminated VM. Or provide the id i.e -p id=<int>',
          'required':
              True
      },
      flags.ID: {
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
      flags.START_TIME_UTC: {
          'type':
              datetime,
          'help':
              'The start window to investigate vm termination. Format: YYYY-MM-DDTHH:MM:SSZ'
      },
      flags.END_TIME_UTC: {
          'type':
              datetime,
          'help':
              'The end window for the investigation. Format: YYYY-MM-DDTHH:MM:SSZ'
      }
  }

  def build_tree(self):
    """Composes the VM runbook tree"""
    start = VmTerminationStart()
    self.add_start(start)
    vm_terminations = NumberOfTerminations()
    self.add_step(parent=start, child=vm_terminations)
    self.add_end(VmTerminationEnd())


class VmTerminationStart(runbook.StartStep):
  """Start VM Termination Checks"""

  def execute(self):
    """Starting VM Termination diagnostics"""
    project = crm.get_project(op.get(flags.PROJECT_ID))
    vm = None
    try:
      name = op.get(flags.NAME) or op.get(flags.ID)
      if name and op.get(flags.ZONE):
        # check VM exists if user provided one
        vm = gce.get_instance(project_id=op.get(flags.PROJECT_ID),
                              zone=op.get(flags.ZONE),
                              instance_name=op.get(flags.NAME))
      elif op.get(flags.NAME) and not op.get(flags.ZONE):
        vm = gce.get_instances(op.context)[flags.NAME]
    except (googleapiclient.errors.HttpError, KeyError):
      op.add_skipped(
          project,
          reason=('Instance {} does not exist in zone {} or project {}').format(
              op.get(flags.NAME), op.get(flags.ZONE), op.get(flags.PROJECT_ID)))
    else:
      if vm and name.isdigit():
        op.put(flags.NAME, vm.name)
      elif vm and not name.isdigit():
        op.put(flags.ID, vm.id)
      op.put(SCOPE_TO_SINGLE_VM, True)


class NumberOfTerminations(runbook.Gateway):
  """A decision point that determines the scope of VM terminations to investigation.

    This class decides whether an investigation should focus on a single termination or
    multiple terminations. It makes this determination based on the operational parameters
    provided to it, specifically checking if the investigation is scoped to a single virtual
    machine (VM).
  """

  def execute(self):
    """Determining whether to investigate one or more terminations"""
    if op.get(SCOPE_TO_SINGLE_VM):
      self.add_child(SingleTerminationCheck())
    else:
      self.add_child(MultipleTerminationCheck())


class SingleTerminationCheck(runbook.Step):
  """Investigates the cause of a single VM termination.

    It analyzes log entries to identify whether the termination was normal or abnormal
    and prepares a Root Cause Analysis (RCA) based on the findings.

    The investigation focuses on the first occurring termination, assuming that any subsequent
    terminations are inconsequential
  """

  template = 'rca::vm_termination'

  def execute(self):
    """Investigating VM termination reason."""
    vm = gce.get_instance(project_id=op.get(flags.PROJECT_ID),
                          zone=op.get(flags.ZONE),
                          instance_name=op.get(flags.NAME))

    log_entries = logs.realtime_query(
        project_id=op.get(flags.PROJECT_ID),
        filter_str=
        f'{LOGGING_FILTER}\nresource.labels.instance_id="{op.get(flags.ID)}"',
        start_time_utc=op.get(flags.START_TIME_UTC),
        end_time_utc=op.get(flags.END_TIME_UTC))

    termination_details: Dict[str, set] = {}
    # TODO: implement https://cloud.google.com/compute/shielded-vm/
    # docs/automating-responses-integrity-failures
    for log_entry in log_entries:
      method = get_path(log_entry, ('protoPayload', 'methodName'), default='')
      principal_email = get_path(
          log_entry, ('protoPayload', 'authenticationInfo', 'principalEmail'),
          default='')
      reason = get_path(log_entry, ('protoPayload', 'status', 'message'),
                        default='')
      timestamp = get_path(log_entry, ('timestamp'), default='')
      insert_id = get_path(log_entry, 'insertId', default='')

      if method in termination_details:
        entries = termination_details.get(method)
        entries.add((insert_id, principal_email, reason, timestamp))
      else:
        termination_details[method] = {
            insert_id, principal_email, reason, timestamp
        }
    if termination_details:
      op.prep_rca(vm,
                  self.template,
                  suffix=op.RCA,
                  kwarg={'termination_details': termination_details})
    else:
      op.add_ok(resource=vm,
                reason=op.prep_msg(op.SUCCESS_REASON,
                                   start_time_utc=op.get(flags.START_TIME_UTC),
                                   end_time_utc=op.get(flags.END_TIME_UTC)))

    status_check = gcp_gs.ResourceAttributeCheck()
    status_check.resource_query = gce.get_instance
    status_check.query_kwargs = {
        'project_id': op.get(flags.PROJECT_ID),
        'zone': op.get(flags.ZONE),
        'instance_name': op.get(flags.NAME)
    }
    status_check.attribute = ('status',)
    status_check.expected_value = 'RUNNING'
    status_check.template = 'gcpdiag.runbook.gce::vm_attributes::terminated_vm_running'
    status_check.extract_args = {
        'vm_name': {
            'source': Resource,
            'attribute': ('name')
        },
        'status': {
            'source': Resource,
            'attribute': ('status')
        }
    }
    self.add_child(status_check)
    self.add_child(VmTerminationEnd())


class MultipleTerminationCheck(runbook.Step):
  """IInvestigates multiple VM terminations within a given project to determine the causes.

    Similar to SingleTerminationCheck, it analyzes log entries but for multiple instances,
    focusing on the first occurring termination per instance to identify normal or abnormal
    patterns.

    Prepares a Root Cause Analysis (RCA) of the terminations based on the gathered details.
  """

  def execute(self):
    """Investigating Reasons for multiple VM termination."""
    log_entries = logs.realtime_query(project_id=op.get(flags.PROJECT_ID),
                                      filter_str=LOGGING_FILTER,
                                      start_time_utc=op.get(
                                          flags.START_TIME_UTC),
                                      end_time_utc=op.get(flags.END_TIME_UTC))

    termination_details: Dict[str, set] = {}

    op.info(f'{len(log_entries)} instance (s) terminated within the timeframe')

    for log_entry in log_entries:
      method = get_path(log_entry, ('protoPayload', 'methodName'), default='')
      principal_email = get_path(
          log_entry, ('protoPayload', 'authenticationInfo', 'principalEmail'),
          default='')
      reason = get_path(log_entry, ('protoPayload', 'status', 'message'),
                        default='')
      timestamp = get_path(log_entry, ('timestamp'), default='')

      insert_id = get_path(log_entry, 'insertId', default='')

      if method in termination_details:
        entries = termination_details.get(method)
        entries.add((insert_id, principal_email, reason, timestamp))
      else:
        termination_details[method] = {
            insert_id, principal_email, reason, timestamp
        }


class VmTerminationEnd(runbook.EndStep):
  """Finalizes the diagnostics process for VM terminations.

  This step prompts the user to confirm
  satisfaction with the Root Cause Analysis (RCA) performed for VM terminations.

  Depending on the user's response, it may conclude the runbook execution or trigger additional
  steps, such as generating a report of the findings.
  """

  def execute(self):
    """Finalize VM terminations diagnostics."""
    response = op.prompt(
        kind=op.CONFIRMATION,
        message='Are you satisfied with the VM termination RCA performed?')
    if response == op.NO:
      op.info(message=op.END_MESSAGE)
      op.interface.rm.generate_report()
