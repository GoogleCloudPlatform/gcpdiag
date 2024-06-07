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
"""Contains diagnostic tree for ops agent onboarding and investigation as well as custom steps."""

from datetime import datetime

import googleapiclient.errors
from boltons.iterutils import get_path

from gcpdiag import runbook
# Interact with GCP APIs using gcpdiag queries
from gcpdiag.queries import crm, gce, iam, logs, monitoring
from gcpdiag.runbook import op
# Reuse generalized steps from other products within this runbook
from gcpdiag.runbook.crm import generalized_steps as crm_gs
from gcpdiag.runbook.gce import constants, flags
from gcpdiag.runbook.gce import generalized_steps as gce_gs
from gcpdiag.runbook.gcp import generalized_steps as gcp_gs
from gcpdiag.runbook.iam import generalized_steps as iam_gs

GAC_SERVICE_ACCOUNT = 'gac_service_account'
CHECK_LOGGING = 'check_logging'
CHECK_MONITORING = 'check_monitoring'
CHECK_SERIAL_PORT_LOGGING = 'check_serial_port_logging'


class OpsAgent(runbook.DiagnosticTree):
  """Investigates the necessary GCP components for the proper functioning of the Ops Agent in a VM

  This runbook will examine the following key areas:

  1. API Service Checks:
    - Ensures that Cloud APIs for Logging and/or Monitoring are accessible.

  2. Permission Checks:
    - Verifies that the necessary permissions are in place for exporting logs and/or metrics.

  3. Workload Authentication:
    - Confirms that the Ops Agent has a service account for authentication.
    - If using Google Application Credentials, provide the service account
      with the `gac_service_account` parameter.

  4. Scope of Investigation:
    - Note that this runbook does not include internal VM checks, such as guest OS investigations.
  """
  parameters = {
      flags.PROJECT_ID: {
          'type': str,
          'help': 'The Project ID containing the VM',
          'required': True
      },
      flags.NAME: {
          'type': str,
          'help': 'Name of the GCE instance running the Ops Agent',
      },
      flags.ID: {
          'type': str,
          'help': 'ID of the GCE instance running the Ops Agent',
      },
      flags.ZONE: {
          'type': str,
          'help': 'Zone of the GCE instance running the Ops Agent',
      },
      flags.START_TIME_UTC: {
          'type': datetime,
          'help': 'Start time of the issue',
      },
      flags.END_TIME_UTC: {
          'type': datetime,
          'help': 'End time of the issue',
      },
      GAC_SERVICE_ACCOUNT: {
          'type':
              str,
          'help':
              'GOOGLE_APPLICATION_CREDENTIALS used by ops agent, if applicable'
      },
      CHECK_LOGGING: {
          'type': bool,
          'help': 'Investigate logging issues',
          'default': True
      },
      CHECK_MONITORING: {
          'type': bool,
          'help': 'Investigate monitoring issues',
          'default': True
      },
      CHECK_SERIAL_PORT_LOGGING: {
          'type': bool,
          'help': 'Check if VM Serial logging is enabled',
          'default': True
      }
  }

  def build_tree(self):
    """Describes step relationships"""
    # Instantiate your start class
    start = OpsAgentStart()
    # add it to your tree
    self.add_start(start)
    sa_check = VmHasAServiceAccount()
    self.add_step(parent=start, child=sa_check)
    self.add_step(parent=sa_check, child=iam_gs.VmHasAnActiveServiceAccount())
    self.add_step(parent=sa_check, child=InvestigateLoggingMonitoring())
    self.add_end(OpsAgentEnd())


class OpsAgentStart(runbook.StartStep):
  """Prepares the parameters required for the gce/ops-agent runbook.

  Looks up the GCE resource running the ops agent binary
  Ensures both instance_id and instance_name parameters are available.
  """

  def execute(self):
    """Verifying context and parameters required for Ops Agent runbook checks"""
    project = crm.get_project(op.get(flags.PROJECT_ID))

    try:
      if not op.get(flags.NAME) and not op.get(flags.ID):
        op.add_skipped(project,
                       reason='Provide an instance name or id to investigate')
        return

      if (op.get(flags.NAME) or op.get(flags.ID)) and op.get(flags.ZONE):
        instance = gce.get_instance(project_id=op.get(flags.PROJECT_ID),
                                    zone=op.get(flags.ZONE),
                                    instance_name=op.get(flags.NAME) or
                                    op.get(flags.ID))
      elif (op.get(flags.NAME) or op.get(flags.ID)) and not op.get(flags.ZONE):
        # find the instance if we only know the instance ID or name
        instances = gce.get_instances(op.context)
        if op.get(flags.ID):
          instance = instances.get(op.get(flags.ID))
        elif op.get(flags.NAME):
          instance = None
          for i in instances.values():
            if i.name.lower() == op.get(flags.NAME).lower():
              instance = i
              break
    except googleapiclient.errors.HttpError:
      op.add_skipped(
          project,
          reason=('Instance {} does not exist in zone {} or project {}').format(
              (op.get(flags.NAME) or op.get(flags.ID)), op.get(flags.ZONE),
              op.get(flags.PROJECT_ID)))
    else:
      # Prepare extra parameters.
      if instance and op.get(flags.NAME):
        op.put(flags.ID, instance.id)

      if instance and op.get(flags.ID):
        op.put(flags.NAME, instance.name)


class VmHasAServiceAccount(runbook.Step):
  """Verifies the existence of a service account for the Ops Agent to use.

  This investigation only happens from the perspective googleapis and
  user provided input. We don't look inside the VM for cases like
  GOOGLE_APPLICATION_CREDENTIALS. User will have to know and specify that if
  They are using the application
  """
  template = 'vm_attributes::service_account_exists'

  def execute(self):
    """Verifying Ops Agent has a service account..."""
    instance = gce.get_instance(project_id=op.get(flags.PROJECT_ID),
                                zone=op.get(flags.ZONE),
                                instance_name=op.get(flags.NAME))

    if not op.get(GAC_SERVICE_ACCOUNT):
      if instance.service_account:
        op.put(flags.SERVICE_ACCOUNT, instance.service_account)
        op.add_ok(instance,
                  reason=op.prep_msg(op.SUCCESS_REASON,
                                     vm_name=instance.name,
                                     sa=instance.service_account))
      else:
        op.add_failed(instance,
                      reason=op.prep_msg(op.FAILURE_REASON,
                                         vm_name=instance.name),
                      remediation=op.prep_msg(op.FAILURE_REMEDIATION))
      return

    if op.get(GAC_SERVICE_ACCOUNT):
      sa_list = iam.get_service_account_list(op.get(flags.PROJECT_ID))
      for sa in sa_list:

        if sa.email == op.get(GAC_SERVICE_ACCOUNT):
          op.put(flags.SERVICE_ACCOUNT, sa.email)
          op.add_ok(instance,
                    reason=op.prep_msg(op.SUCCESS_REASON,
                                       vm_name=instance.name,
                                       sa=sa.email))
          break
    elif not op.get(GAC_SERVICE_ACCOUNT) and not instance.service_account:
      op.add_failed(instance,
                    reason=op.prep_msg(op.FAILURE_REASON,
                                       vm_name=instance.name),
                    remediation=op.prep_msg(op.FAILURE_REMEDIATION))


class InvestigateLoggingMonitoring(runbook.Gateway):
  """A Decision Point for to check Logging and/or Monitoring related issues

  Decides whether to check for ops agent
   - logging related issues if CHECK_LOGGING is set to true
   - monitoring related issues if CHECK_MONITORING is set to true
  """

  def execute(self):
    """Decision point to investigate Logging and/or Monitoring related issues."""
    if op.get(CHECK_LOGGING):
      logging_api = gcp_gs.ServiceApiStatusCheck()
      logging_api.api_name = 'logging'
      logging_api.expected_state = constants.APIState.ENABLED
      self.add_child(logging_api)

      log_permission_check = iam_gs.IamPolicyCheck()
      log_permission_check.principal = f'serviceAccount:{op.get(flags.SERVICE_ACCOUNT)}'
      log_permission_check.roles = [
          'roles/owner', 'roles/editor', 'roles/logging.logWriter',
          'roles/logging.admin'
      ]
      logging_api.add_child(log_permission_check)
      logging_access_scope = gce_gs.VmScope()
      logging_access_scope.access_scopes = {
          'https://www.googleapis.com/auth/logging.write',
          'https://www.googleapis.com/auth/cloud-platform',
          'https://www.googleapis.com/auth/logging.admin'
      }
      logging_api.add_child(logging_access_scope)

      logging_subagent_check = gce_gs.VmHasOpsAgent()
      logging_subagent_check.check_logging = True
      logging_subagent_check.check_metrics = False
      logging_access_scope.add_child(logging_subagent_check)

      if op.get(CHECK_SERIAL_PORT_LOGGING):
        logging_api.add_child(child=CheckSerialPortLogging())

    if op.get(CHECK_MONITORING):
      monitoring_api = gcp_gs.ServiceApiStatusCheck()
      monitoring_api.api_name = 'monitoring'
      monitoring_api.expected_state = constants.APIState.ENABLED
      self.add_child(monitoring_api)

      monitoring_permission_check = iam_gs.IamPolicyCheck()
      monitoring_permission_check.principal = f'serviceAccount:{op.get(flags.SERVICE_ACCOUNT)}'
      monitoring_permission_check.roles = [
          'roles/monitoring.metricWriter', 'roles/monitoring.admin',
          'roles/monitoring.editor', 'roles/owner', 'roles/editor'
      ]
      monitoring_api.add_child(child=monitoring_permission_check)
      monitoring_access_scope = gce_gs.VmScope()
      monitoring_access_scope.access_scopes = {
          'https://www.googleapis.com/auth/monitoring.write',
          'https://www.googleapis.com/auth/cloud-platform',
          'https://www.googleapis.com/auth/monitoring'
      }
      monitoring_api.add_child(monitoring_access_scope)
      # Check if ops agent metric subagent is installed.
      metric_subagent_check = gce_gs.VmHasOpsAgent()
      metric_subagent_check.check_logging = False
      metric_subagent_check.check_metrics = True
      monitoring_access_scope.add_child(metric_subagent_check)


class CheckSerialPortLogging(runbook.CompositeStep):
  """Checks if ops agent serial port logging

  Verifies Organization policy and VM configuration to issue serial port logging
  to Stackdriver from Compute Engine VMs is feasible.
  """

  def execute(self):
    """Verifying GCP config required for serial port logging with ops agent"""
    serial_logging_orgpolicy_check = crm_gs.OrgPolicyCheck()
    serial_logging_orgpolicy_check.constraint = 'constraints/compute.disableSerialPortLogging'
    serial_logging_orgpolicy_check.is_enforced = False
    self.add_child(serial_logging_orgpolicy_check)

    serial_logging_md_check = gce_gs.VmMetadataCheck()
    serial_logging_md_check.metadata_key = 'serial-port-logging-enable'
    serial_logging_md_check.expected_value = True
    self.add_child(serial_logging_md_check)


class OpsAgentEnd(runbook.EndStep):
  """Finalizes the OpsAgent checks.

  Checks if logs or metrics are currently present after diagnosing the issue.
  """

  def _has_ops_agent_metric_logging_agent(self, metric_data):
    """Checks if ops agent logging agent and metric agent is installed"""
    pass

  def execute(self):
    """Finalizing Ops agent checks"""
    serial_log_entries = None
    has_expected_opsagent_logs = False
    ops_agent_uptime = None
    has_opsagent = False
    if op.get(CHECK_SERIAL_PORT_LOGGING):
      serial_log_entries = logs.realtime_query(
          project_id=op.get(flags.PROJECT_ID),
          filter_str='''resource.type="gce_instance"
                        log_name="projects/{}/logs/ops-agent-health"
                        resource.labels.instance_id="{}" AND
                        "LogPingOpsAgent"'''.format(op.get(flags.PROJECT_ID),
                                                    op.get(flags.ID)),
          start_time_utc=op.get(flags.END_TIME_UTC),
          end_time_utc=datetime.now())
      if serial_log_entries:
        has_expected_opsagent_logs = True
        op.info(
            'There are new logs indicating ops agent is exporting serial logs')

    if op.get(CHECK_MONITORING):
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

      for entry in ops_agent_uptime.values():
        version = get_path(entry, ('labels', 'metric.version'), '')
        if 'google-cloud-ops-agent-metrics' in version:
          has_opsagent = True
          op.info(
              'There is metrics data indicating ops agent is exporting metrics correctly!'
          )

      if not has_expected_opsagent_logs and not has_opsagent:
        response = op.prompt(
            kind=op.CONFIRMATION,
            message=
            f'Is your ops agent issues resolved for "{op.get(flags.NAME)}?"')
        if response == op.NO:
          op.info(message=op.END_MESSAGE)
