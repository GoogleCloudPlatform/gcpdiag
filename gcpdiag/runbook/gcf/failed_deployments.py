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
"""Cloud Run function failed deployments check"""

from datetime import datetime

import googleapiclient.errors
from boltons.iterutils import get_path

from gcpdiag import config, runbook
from gcpdiag.queries import crm, iam, logs
from gcpdiag.runbook import op
from gcpdiag.runbook.gcf import constants as gcf_const
from gcpdiag.runbook.gcf import flags
from gcpdiag.runbook.iam import generalized_steps as iam_gs


class FailedDeployments(runbook.DiagnosticTree):
  """ Cloud Run function failed deployments check

  This runbook will assist users to check reasons for failed deployments of Gen2 cloud functions.
  Current basic Validations:
  - Check for existence of Default SA
  - Check for existence of Cloud function Service Agent
  - Check for existence of cloud functions Service Agent and its permissions
  - Check for error logs for global scope code errors and resource location constraint.
  """
  parameters = {
      flags.PROJECT_ID: {
          'type': str,
          'help': 'The Project ID containing the cloud function',
          'required': True
      },
      flags.NAME: {
          'type': str,
          'help': 'Name of the cloud function failing deployment',
          'required': True
      },
      flags.REGION: {
          'type': str,
          'help': 'Region of the cloud function failing deployment',
          'required': True
      },
      flags.START_TIME: {
          'type': datetime,
          'help': 'Start time of the issue Format: YYYY-MM-DDTHH:MM:SSZ',
      },
      flags.END_TIME: {
          'type': datetime,
          'help': 'End time of the issue. Format: YYYY-MM-DDTHH:MM:SSZ',
      },
      flags.GAC_SERVICE_ACCOUNT: {
          'type': str,
          'help': 'Service account used by the user for deployment.'
      }
  }

  def build_tree(self):
    """Construct the diagnostic tree with appropriate steps."""
    start = FailedDeploymentsStart()
    self.add_start(start)
    custom = DefaultServiceAccountCheck()
    self.add_step(parent=start, child=custom)
    self.add_step(parent=custom, child=UserServiceAccountCheck())
    self.add_step(parent=custom, child=FunctionGlobalScopeCheck())
    self.add_step(parent=custom, child=LocationConstraintCheck())
    self.add_end(FailedDeploymentEndStep())


class FailedDeploymentsStart(runbook.StartStep):
  """Check for function status and existence of function in project."""

  def execute(self):
    """Check if cloud function region and name is specified."""
    project = crm.get_project(op.get(flags.PROJECT_ID))
    if not project:
      op.add_skipped(
          project, reason=f'Project {op.get(flags.PROJECT_ID)} does not exist')


class DefaultServiceAccountCheck(runbook.Step):
  """Check if cloud run function default service account and agent exists and is enabled."""

  template = 'failed_deployments::default_service_account_check'

  def execute(self):
    """Check if cloud run function default service account and agent exists and is enabled."""

    project_num = crm.get_project(op.get(flags.PROJECT_ID)).number
    service_agent = ('service-{}@gcf-admin-robot.iam.gserviceaccount.com'
                    ).format(project_num)
    default_sa = (
        '{}-compute@developer.gserviceaccount.com').format(project_num)
    project = crm.get_project(op.get(flags.PROJECT_ID))
    try:
      if iam.is_service_account_existing(service_agent, op.get(
          flags.PROJECT_ID)) and iam.is_service_account_enabled(
              service_agent, op.get(flags.PROJECT_ID)):
        console_permission = iam_gs.IamPolicyCheck()
        console_permission.template = 'failed_deployments::agent_permission'
        console_permission.principal = f'serviceAccount:{service_agent}'
        console_permission.roles = [gcf_const.SERVICE_AGENT_ROLE]
        console_permission.require_all = False
        self.add_child(console_permission)
    except googleapiclient.errors.HttpError as err:
      if err.code == 404:
        op.add_skipped(
            project,
            reason=('Service agent {} does not exist on project {}').format(
                service_agent, op.get(flags.PROJECT_ID)))
      else:
        op.add_skipped(
            project,
            reason=('Service agent {} is not enabled on project {}').format(
                service_agent, op.get(flags.PROJECT_ID)))

    if iam.is_service_account_existing(default_sa, op.get(
        flags.PROJECT_ID)) and iam.is_service_account_enabled(
            default_sa, op.get(flags.PROJECT_ID)):
      op.add_ok(project, reason=op.prep_msg(op.SUCCESS_REASON))
    else:
      op.add_failed(project,
                    reason=op.prep_msg(op.FAILURE_REASON),
                    remediation=op.prep_msg(op.FAILURE_REMEDIATION))


class UserServiceAccountCheck(runbook.Step):
  """Check if User/Service account has permissions on Cloud function runtime service account"""

  template = 'failed_deployments::user_service_account_check'

  def execute(self):
    """Check if User/Service account has permissions on Cloud function runtime service account"""

    name = op.get(flags.NAME)

    project = crm.get_project(op.get(flags.PROJECT_ID))
    project_num = crm.get_project(op.get(flags.PROJECT_ID)).number
    logging_filter = '''
      protoPayload.methodName=("google.cloud.functions.v2.FunctionService.UpdateFunction"
      OR "google.cloud.functions.v2.FunctionService.CreateFunction")
      protoPayload.resourceName =~ "{}"
      severity=NOTICE'''.format(name)

    try:
      log_entries = logs.realtime_query(project_id=op.get(flags.PROJECT_ID),
                                        filter_str=logging_filter,
                                        start_time=op.get(flags.START_TIME),
                                        end_time=op.get(flags.END_TIME))
      latest_entry = log_entries[-1]
      user_principal = get_path(
          latest_entry,
          ('protoPayload', 'authenticationInfo', 'principalEmail'),
          default='')

      runtime_account = f'{project_num}-compute@developer.gserviceaccount.com'
      policy_list = iam.get_service_account_iam_policy(op.get(flags.PROJECT_ID),
                                                       runtime_account)

      #Check if User account/Service account has 'roles/iam.serviceAccountUser'
      #permissions on Cloud function runtime service account

      user_principal_sa = 'serviceAccount:' + user_principal
      user_principal_user = 'user:' + user_principal
      if policy_list.has_role_permissions(
          user_principal_sa,
          gcf_const.USER_PRINCIPAL_ROLE) or policy_list.has_role_permissions(
              user_principal_user, gcf_const.USER_PRINCIPAL_ROLE):
        op.add_ok(project,
                  reason=op.prep_msg(op.SUCCESS_REASON,
                                     user_principal=user_principal,
                                     runtime_account=runtime_account))
      else:
        op.add_failed(project,
                      reason=op.prep_msg(op.FAILURE_REASON,
                                         user_principal=user_principal,
                                         runtime_account=runtime_account),
                      remediation=op.prep_msg(op.FAILURE_REMEDIATION))

    except googleapiclient.errors.HttpError:
      op.add_skipped(
          project,
          reason=(
              'No function failure log entries found for project {}').format(
                  op.get(flags.PROJECT_ID)))


class FunctionGlobalScopeCheck(runbook.Step):
  """Check for deployment failures due to global scope code errors"""

  template = 'failed_deployments::global_scope_check'

  def execute(self):
    """Check for deployment failures due to global scope code errors"""
    name = op.get(flags.NAME)
    project = crm.get_project(op.get(flags.PROJECT_ID))
    global_scope_filter = '''
      resource.type="cloud_function"
      SEARCH("Could not create or update Cloud Run service {},
      Container Healthcheck failed.")'''.format(name)

    global_log_entries = logs.realtime_query(
        project_id=op.get(flags.PROJECT_ID),
        filter_str=global_scope_filter,
        start_time=op.get(flags.START_TIME),
        end_time=op.get(flags.END_TIME))

    if global_log_entries:
      op.add_failed(project,
                    reason=op.prep_msg(op.FAILURE_REASON),
                    remediation=op.prep_msg(op.FAILURE_REMEDIATION))
    else:
      op.add_ok(project, reason=op.prep_msg(op.SUCCESS_REASON))


class LocationConstraintCheck(runbook.Step):
  """Check for deployment failures due to resource location constraint"""

  template = 'failed_deployments::location_constraint_check'

  def execute(self):
    """Check for deployment failures due to resource location constraint"""

    #Identify deployment failures due to resource location org policy constraints.
    project = crm.get_project(op.get(flags.PROJECT_ID))
    location_constraint_filter = '''
      resource.type="cloud_function"
      SEARCH("Constraint `constraints/gcp.resourceLocations` violated")'''

    location_log_entries = logs.realtime_query(
        project_id=op.get(flags.PROJECT_ID),
        filter_str=location_constraint_filter,
        start_time=op.get(flags.START_TIME),
        end_time=op.get(flags.END_TIME))

    if location_log_entries:
      op.add_failed(project,
                    reason=op.prep_msg(op.FAILURE_REASON),
                    remediation=op.prep_msg(op.FAILURE_REMEDIATION))
    else:
      op.add_ok(project, reason=op.prep_msg(op.SUCCESS_REASON))


class FailedDeploymentEndStep(runbook.EndStep):
  """Finalizing cloud run function deployment failures """

  def execute(self):
    """Finalizing cloud run function deployment failures """
    response = None
    if not config.get(flags.INTERACTIVE_MODE):
      response = op.prompt(kind=op.CONFIRMATION,
                           message=('Were you able to troubleshoot effectively'
                                    ' your Cloud Run Function deployment?'),
                           choice_msg='Enter an option: ')
    if response == op.NO:
      op.info(message=op.END_MESSAGE)
