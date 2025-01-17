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
"""Module containing Dataflow Jobs permissions check diagnostic tree and custom steps."""

from gcpdiag import runbook
from gcpdiag.queries import crm, iam, logs
from gcpdiag.runbook import StartStep, op
from gcpdiag.runbook.crm import generalized_steps as crm_gs
from gcpdiag.runbook.dataflow import constants as dataflow_constants
from gcpdiag.runbook.dataflow import flags
from gcpdiag.runbook.iam import generalized_steps as iam_gs

PRODUCT_FLAG = 'dataflow'


def local_realtime_query(filter_str):
  result = logs.realtime_query(
      project_id=op.get(flags.PROJECT_ID),
      start_time_utc=op.get(flags.START_TIME_UTC),
      end_time_utc=op.get(flags.END_TIME_UTC),
      filter_str=filter_str,
  )
  return result


class JobPermissions(runbook.DiagnosticTree):
  """Analysis and Resolution of Dataflow Jobs Permissions issues.

  This runbook investigates Dataflow permissions and recommends remediation steps.

  Areas Examined:
  - Dataflow User Account Permissions: Verify that individual Dataflow users have the necessary
    permissions to access and manage Dataflow jobs (e.g., create,update,cancel).

  - Dataflow Service Account Permissions: Verify that the Dataflow Service Account has the required
    permissions to execute and manage the Dataflow jobs

  - Dataflow Worker Service Account: Verify that the Dataflow Worker Service Account has the
    necessary permissions for worker instances within a Dataflow job to access input and
    output resources during job execution.

  - Dataflow Resource Permissions: Verify that Dataflow resources (e.g., Cloud Storage buckets,
    BigQuery datasets) have the necessary permissions to be accessed and used by Dataflow jobs.

  By ensuring that Dataflow resources have the necessary permissions, you
  can prevent errors and ensure that your jobs run smoothly.
  """

  parameters = {
      flags.PROJECT_ID: {
          'type': str,
          'help': 'The Project ID of the resource under investigation',
          'required': True,
      },
      flags.PRINCIPAL: {
          'type': str,
          'help': ('The authenticated user account email. This is the '
                   'user account that is used to authenticate the user to the '
                   'console or the gcloud CLI.'),
          'required': True,
      },
      flags.WORKER_SERVICE_ACCOUNT: {
          'type': str,
          'help':
              ('Dataflow Worker Service Account used for Dataflow Job Creation'
               'and execution'),
          'required': True,
      },
      flags.CROSS_PROJECT_ID: {
          'type':
              str,
          'help':
              ('Cross Project ID, where service account is located if it is not'
               ' in the same project as the Dataflow Job'),
      },
  }

  def build_tree(self):
    """Construct the diagnostic tree with appropriate steps."""
    # Instantiate your step classes
    start = StartStep()
    user_account_permissions_check = DataflowUserAccountPermissions()
    worker_service_account_check = DataflowWorkerServiceAccountPermissions()
    dataflow_resource_permissions_check = DataflowResourcePermissions()

    self.add_start(start)
    self.add_step(parent=start, child=user_account_permissions_check)

    project = crm.get_project(op.get(flags.PROJECT_ID))
    service_agent_check = iam_gs.IamPolicyCheck()
    service_agent_check.roles = [dataflow_constants.DATAFLOW_SERVICE_AGENT_ROLE]
    service_agent_check.principal = f'serviceAccount:service-{project.number}@dataflow-service-producer-prod.iam.gserviceaccount.com'  # pylint: disable=line-too-long
    service_agent_check.template = 'gcpdiag.runbook.dataflow::permissions::dataflow_service_account'  # pylint: disable=line-too-long
    service_agent_check.require_all = False
    self.add_step(parent=start, child=service_agent_check)

    self.add_step(parent=start, child=worker_service_account_check)
    self.add_step(parent=start, child=dataflow_resource_permissions_check)
    self.add_end(DataflowPermissionsEnd())


class DataflowUserAccountPermissions(runbook.Step):
  """Check the User account permissions.

  "Dataflow Viewer" role allows the user to view/list the Dataflow jobs. But,
  cannot submit, update, drain, stop, or cancel the jobs.
  "Dataflow Developer" role does allows the user to create and modify (view,
  update, cancel etc) the dataflow jobs, but does not provide machine type,
  storage bucket configuration access.
  "Dataflow Admin" role provides complete access for creating and modifying the
  jobs along with the machine type and storage bucket configuration access.
  """

  def execute(self):
    """Check the Authenticated User account permissions."""
    dataflow_developer_role_check = iam_gs.IamPolicyCheck()
    dataflow_developer_role_check.roles = [
        dataflow_constants.DATAFLOW_DEVELOPER_ROLE,
        dataflow_constants.DATAFLOW_IAM_SERVICE_ACCOUNT_USER,
    ]
    dataflow_developer_role_check.principal = f'user:{op.get(flags.PRINCIPAL)}'
    dataflow_developer_role_check.require_all = True
    self.add_child(dataflow_developer_role_check)


class DataflowWorkerServiceAccountPermissions(runbook.Gateway):
  """Check the Dataflow Worker account permissions.

  Worker instances use the worker service account to access input and output
  resources after you submit your job.
  For the worker service account to be able to run a job,
  it must have the roles/dataflow.worker role.
  """
  template = 'permissions::projectcheck'

  def execute(self):
    """Checking dataflow worker service account permissions."""
    sa_email = op.get(flags.WORKER_SERVICE_ACCOUNT)
    project = crm.get_project(op.get(flags.PROJECT_ID))
    op.info(op.get(flags.WORKER_SERVICE_ACCOUNT))
    sa_exists = iam.is_service_account_existing(email=sa_email,
                                                billing_project_id=op.get(
                                                    flags.PROJECT_ID))
    sa_exists_cross_project = iam.is_service_account_existing(
        email=sa_email, billing_project_id=op.get(flags.CROSS_PROJECT_ID))
    if sa_exists and op.get(flags.CROSS_PROJECT_ID) is None:
      op.info('Service Account associated with Dataflow Job was found in the'
              ' same project')
      op.info('Checking permissions.')
      # Check for Service Account permissions
      sa_permission_check = iam_gs.IamPolicyCheck()
      sa_permission_check.project = op.get(flags.PROJECT_ID)
      sa_permission_check.principal = (
          f'serviceAccount:{op.get(flags.WORKER_SERVICE_ACCOUNT)}')
      sa_permission_check.template = 'gcpdiag.runbook.dataflow::permissions::dataflow_worker_service_account'  # pylint: disable=line-too-long
      sa_permission_check.require_all = True
      sa_permission_check.roles = [dataflow_constants.DATAFLOW_WORKER_ROLE]
      self.add_child(child=sa_permission_check)
    elif sa_exists_cross_project:
      op.info('Service Account associated with Dataflow Job was found in cross '
              'project')
      # Check if constraint is enforced
      op.info('Checking constraints on service account project.')
      orgpolicy_constraint_check = crm_gs.OrgPolicyCheck()
      orgpolicy_constraint_check.project = op.get(flags.CROSS_PROJECT_ID)
      orgpolicy_constraint_check.constraint = (
          'constraints/iam.disableCrossProjectServiceAccountUsage')
      orgpolicy_constraint_check.is_enforced = False
      self.add_child(orgpolicy_constraint_check)

      # Check Service Account roles
      op.info('Checking roles in service account project.')
      sa_permission_check = iam_gs.IamPolicyCheck()
      sa_permission_check.project = op.get(flags.CROSS_PROJECT_ID)
      sa_permission_check.principal = (
          f'serviceAccount:{op.get(flags.WORKER_SERVICE_ACCOUNT)}')
      sa_permission_check.template = 'gcpdiag.runbook.dataflow::permissions::dataflow_cross_project_worker_service_account'  # pylint: disable=line-too-long
      sa_permission_check.require_all = True
      sa_permission_check.roles = [dataflow_constants.DATAFLOW_WORKER_ROLE]
      self.add_child(child=sa_permission_check)

      # Check Service Agent Service Account roles
      op.info('Checking service agent service account roles on service account '
              'project.')
      service_agent_sa = (
          f'service-{project.number}@dataflow-service-producer-prod.iam.gserviceaccount.com'
      )
      service_agent_permission_check = iam_gs.IamPolicyCheck()
      service_agent_permission_check.project = op.get(flags.CROSS_PROJECT_ID)
      service_agent_permission_check.principal = (
          f'serviceAccount:{service_agent_sa}')
      service_agent_permission_check.template = 'gcpdiag.runbook.dataflow::permissions::dataflow_cross_project_worker_service_account'  # pylint: disable=line-too-long
      service_agent_permission_check.require_all = True
      service_agent_permission_check.roles = [
          dataflow_constants.DATAFLOW_IAM_SERVICE_ACCOUNT_USER,
          'roles/iam.serviceAccountTokenCreator'
      ]
      self.add_child(child=service_agent_permission_check)

      # Check Compute Agent Service Account
      op.info('Checking compute agent service account roles on service account '
              'project.')
      compute_agent_sa = (
          f'service-{project.number}@compute-system.iam.gserviceaccount.com')
      compute_agent_permission_check = iam_gs.IamPolicyCheck()
      compute_agent_permission_check.project = op.get(flags.CROSS_PROJECT_ID)
      compute_agent_permission_check.principal = (
          f'serviceAccount:{compute_agent_sa}')
      compute_agent_permission_check.template = 'gcpdiag.runbook.dataflow::permissions::dataflow_cross_project_worker_service_account'  # pylint: disable=line-too-long
      compute_agent_permission_check.require_all = True
      compute_agent_permission_check.roles = [
          dataflow_constants.DATAFLOW_IAM_SERVICE_ACCOUNT_USER,
          'roles/iam.serviceAccountTokenCreator'
      ]
      self.add_child(child=compute_agent_permission_check)
    else:
      op.add_failed(project,
                    reason=op.prep_msg(op.FAILURE_REASON,
                                       service_account=op.get(
                                           flags.WORKER_SERVICE_ACCOUNT),
                                       project_id=op.get(flags.PROJECT_ID)),
                    remediation=op.prep_msg(op.FAILURE_REMEDIATION))


class DataflowResourcePermissions(runbook.Step):
  """Check the Dataflow Resource permissions.

  Verify that Dataflow resources have the necessary permissions to be accessed
  and used by Dataflow jobs.
  Ensure that the your Dataflow project Worker Service Account have the
  required permissions to access and modify these resources.
  """

  def execute(self):
    """Check the Dataflow Resource permissions."""
    filter_str = [
        'log_id("dataflow.googleapis.com/job-message")',
        'resource.type="dataflow_step"',
        ('textPayload=~("Failed to write a file to temp location" OR "Unable'
         ' to rename output files" OR "Unable to delete temp files")'),
    ]
    filter_str = '\n'.join(filter_str)
    log_entries = local_realtime_query(filter_str)
    if log_entries:
      op.info('Cloud Storage buckets related errors found in the logs..')
      op.info('Checking worker service account storage object admin role.')
      dataflow_storage_role_check = iam_gs.IamPolicyCheck()
      if op.get(flags.CROSS_PROJECT_ID):
        dataflow_storage_role_check.project = op.get(flags.CROSS_PROJECT_ID)
      dataflow_storage_role_check.roles = ['roles/storage.objectAdmin']
      dataflow_storage_role_check.principal = (
          f'serviceAccount:{op.get(flags.WORKER_SERVICE_ACCOUNT)}')
      dataflow_storage_role_check.require_all = True
      self.add_child(dataflow_storage_role_check)
    else:
      op.info('No Cloud Storage buckets related errors found in the logs')


class DataflowPermissionsEnd(runbook.EndStep):
  """RUNBOOK COMPLETED."""

  def execute(self):
    """Permissions checks completed."""
    op.info('Dataflow Resources Permissions Checks Completed')
