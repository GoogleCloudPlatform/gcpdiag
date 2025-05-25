# Copyright 2025 Google LLC
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
"""Runbook for diagnosing VM creation issues."""

from datetime import datetime

from boltons.iterutils import get_path

from gcpdiag import runbook
from gcpdiag.queries import crm, logs
from gcpdiag.runbook import op
from gcpdiag.runbook.gce import flags

VM_CREATION_FAILURE_FILTER = '''
    resource.type="gce_instance"
    log_id("cloudaudit.googleapis.com/activity")
    protoPayload.resourceName="projects/{PROJECT_ID}/zones/{ZONE}/instances/{INSTANCE_NAME}"
    protoPayload.methodName=~"compute.instances.insert"
    severity=ERROR AND
    (protoPayload.status.message="QUOTA_EXCEEDED" OR
    protoPayload.response.error.errors.reason="alreadyExists" OR
    protoPayload.response.error.message=~"Required '.*' permission for '.*'")
    '''


class VmCreation(runbook.DiagnosticTree):
  """Runbook for diagnosing VM creation issues.

    This runbook helps identify and resolve issues related to VM creation in Google Cloud.

    - Checks for quota-related issues.
    - Checks for permission-related issues.
    - Checks for conflicts such as resource already existing.
  """
  parameters = {
      flags.PROJECT_ID: {
          'type': str,
          'help': 'The Project ID which will host the VM to be created.',
          'required': True
      },
      flags.INSTANCE_NAME: {
          'type': str,
          'help': 'The name of the VM to be created.',
          'required': True
      },
      flags.ZONE: {
          'type': str,
          'help': 'The Google Cloud zone of the VM to be created.',
          'required': True
      },
      flags.PRINCIPAL: {
          'type': str,
          'help': 'The authenticated principal that initiated the VM creation.'
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
      }
  }

  def build_tree(self):
    """Construct the diagnostic tree with appropriate steps."""
    start = runbook.StartStep()
    # add them to your tree
    self.add_start(start)
    self.add_step(parent=start, child=InvestigateVmCreationLogFailure())
    # Ending your runbook
    self.add_end(runbook.EndStep())


class InvestigateVmCreationLogFailure(runbook.Gateway):
  """Investigate VM creation failure logs.

    This step queries logs to identify the root cause of VM creation failures,
    such as quota issues, permission errors, or resource conflicts.
    """
  template = 'vm_creation::logs'

  def execute(self):
    """Query logs to determine the cause of VM creation failure."""
    project = crm.get_project(op.get(flags.PROJECT_ID))
    res = logs.realtime_query(project_id=op.get(flags.PROJECT_ID),
                              filter_str=VM_CREATION_FAILURE_FILTER.format(
                                  PROJECT_ID=op.get(flags.PROJECT_ID),
                                  ZONE=op.get(flags.ZONE),
                                  INSTANCE_NAME=op.get(flags.INSTANCE_NAME)),
                              start_time=datetime.now(),
                              end_time=op.get(flags.END_TIME))

    if res:
      entry = res[0]
      error_message = get_path(
          entry, ('protoPayload', 'response', 'error', 'errors', 0, 'message'))
      error_reason = get_path(
          entry, ('protoPayload', 'response', 'error', 'errors', 0, 'reason'))
      status_message = get_path(entry, ('protoPayload', 'status', 'message'))
      if status_message and status_message == 'QUOTA_EXCEEDED':
        error_message = status_message

        metric_name = get_path(entry, ('protoPayload', 'status', 'details',
                                       'quotaExceeded', 'metricName'))
        limit = get_path(
            entry,
            ('protoPayload', 'status', 'details', 'quotaExceeded', 'limit'))
        limit_name = get_path(
            entry,
            ('protoPayload', 'status', 'details', 'quotaExceeded', 'limitName'))

        op.add_failed(project,
                      reason=op.prep_msg(op.FAILURE_REASON_ALT1,
                                         error_message=error_message),
                      remediation=op.prep_msg(op.FAILURE_REMEDIATION_ALT1,
                                              metric_name=metric_name,
                                              limit=limit,
                                              limit_name=limit_name))
      elif error_reason and error_reason == 'alreadyExists':
        op.add_failed(project,
                      reason=op.prep_msg(op.FAILURE_REASON,
                                         error_message=error_message),
                      remediation=op.prep_msg(
                          op.FAILURE_REMEDIATION,
                          zone=op.get(flags.ZONE),
                          project_id=op.get(flags.PROJECT_ID),
                          instance_name=op.get(flags.INSTANCE_NAME)))
      elif error_reason and error_reason == 'forbidden':
        op.add_failed(project,
                      reason=op.prep_msg(op.FAILURE_REASON_ALT2,
                                         error_message=error_message),
                      remediation=op.prep_msg(op.FAILURE_REMEDIATION_ALT2))
