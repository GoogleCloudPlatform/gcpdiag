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
"""Module containing Dataproc Spark job failures diagnostic tree and custom steps."""

from datetime import datetime, timedelta, timezone

from packaging import version

from gcpdiag import runbook
from gcpdiag.queries import crm, dataproc, iam, logs
from gcpdiag.runbook import op
from gcpdiag.runbook.crm import generalized_steps as crm_gs
from gcpdiag.runbook.dataproc import constants as dp_const
from gcpdiag.runbook.dataproc import flags
from gcpdiag.runbook.dataproc import generalized_steps as dp_gs
from gcpdiag.runbook.iam import generalized_steps as iam_gs
from gcpdiag.utils import GcpApiError


class SparkJobFailures(runbook.DiagnosticTree):
  """Provides a comprehensive analysis of common issues which affects Dataproc Spark job failures.

  This runbook focuses on a range of potential problems for Dataproc Spark jobs
  on
  Google Cloud Platform. By conducting a series of checks, the runbook aims to
  pinpoint the root cause of Spark job failures.

  The following areas are examined:

  - Cluster version supportability: Evaluates if the job was run on a supported
  cluster image version.
  - Permissions: Checks for permission related issues on the cluster and GCS
  bucket level.
  - OOM: Checks Out-Of-Memory issues for the Spark job on master or worker
  nodes.
  - Logs: Check other logs related to shuffle failures, broken pipe, YARN
  runtime exception, import failures.
  - Throttling: Checks if the job was throttled and provides the exact reason
  for it.
  - GCS Connector: Evaluates possible issues with the GCS Connector.
  - BigQuery Connector: Evaluates possible issues with BigQuery Connector, such
  as dependency version conflicts.
  """

  parameters = {
      flags.PROJECT_ID: {
          'type': str,
          'help': 'The Project ID of the resource under investigation',
          'required': True,
      },
      flags.JOB_ID: {
          'type': str,
          'help': 'The Job ID of the resource under investigation',
          'deprecated': True,
          'new_parameter': 'dataproc_job_id'
      },
      flags.DATAPROC_JOB_ID: {
          'type': str,
          'help': 'The Job ID of the resource under investigation',
          'required': True,
      },
      flags.REGION: {
          'type': str,
          'help': 'Dataproc job/cluster Region',
          'required': True,
      },
      flags.ZONE: {
          'type': str,
          'help': 'Dataproc cluster Zone',
      },
      flags.SERVICE_ACCOUNT: {
          'type':
              str,
          'help':
              ('Dataproc cluster Service Account used to create the resource'),
      },
      flags.CROSS_PROJECT_ID: {
          'type':
              str,
          'help':
              ('Cross Project ID, where service account is located if it is not'
               ' in the same project as the Dataproc cluster'),
      },
      flags.STACKDRIVER: {
          'type': str,
          'help': ('Checks if stackdriver logging is enabled for further'
                   ' troubleshooting'),
          'default': False,
      },
  }

  def legacy_parameter_handler(self, parameters):
    if flags.JOB_ID in parameters:
      parameters[flags.DATAPROC_JOB_ID] = parameters.pop(flags.JOB_ID)

  def build_tree(self):
    """Dataproc Spark Job Failures debug tree."""
    # Instantiate your step classes
    job_exist = JobExists()
    self.add_start(job_exist)
    # Check cluster exists
    cluster_exists = DataProcClusterExists()
    self.add_step(parent=job_exist, child=cluster_exists)
    # Check stackdriver enabled
    stackdriver_setting = CheckStackdriverSetting()
    self.add_step(parent=cluster_exists, child=stackdriver_setting)
    # Check cluster version
    cluster_version = CheckClusterVersion()
    self.add_step(parent=stackdriver_setting, child=cluster_version)
    # Check if job failed
    check_if_job_failed = CheckIfJobFailed()
    self.add_step(parent=cluster_version, child=check_if_job_failed)
    # Check if job failed due to task not found
    check_task_not_found = CheckTaskNotFound()
    self.add_step(parent=check_if_job_failed, child=check_task_not_found)
    # Check if permissions meet requirements
    check_permissions = CheckPermissions()
    self.add_step(parent=check_task_not_found, child=check_permissions)
    # Check if Master OOM happened
    check_master_oom = CheckMasterOOM()
    self.add_step(parent=check_task_not_found, child=check_master_oom)
    # Check if worker OOM happened
    check_worker_oom = CheckWorkerOOM()
    self.add_step(parent=check_master_oom, child=check_worker_oom)
    # Check if secodnary worker preemption happened
    check_sw_preemption = CheckSWPreemption()
    self.add_step(parent=check_worker_oom, child=check_sw_preemption)
    # Check if worker disk usage issue happened
    check_worker_disk_usage_issue = CheckWorkerDiskUsageIssue()
    self.add_step(parent=check_worker_oom, child=check_worker_disk_usage_issue)
    # Check cluster network connection
    check_cluster_network = dp_gs.CheckClusterNetworkConnectivity()
    self.add_step(parent=check_worker_oom, child=check_cluster_network)
    # Check if job failed due to port exhaustion
    check_port_exhaustion = CheckPortExhaustion()
    self.add_step(parent=check_cluster_network, child=check_port_exhaustion)
    # Check if killing orphaned application happened
    check_killing_orphaned_application = CheckKillingOrphanedApplication()
    self.add_step(parent=check_cluster_network,
                  child=check_killing_orphaned_application)
    # Check if python import failure happened
    check_python_import_failure = CheckPythonImportFailure()
    self.add_step(
        parent=check_cluster_network,
        child=check_python_import_failure,
    )
    # Check for logs indicating shuffle failures.
    check_shuffle_failures = CheckShuffleFailures()
    self.add_step(parent=check_cluster_network, child=check_shuffle_failures)
    # Check if fetch job failed with executor is not registered error
    check_shuffle_service_kill = CheckShuffleServiceKill()
    self.add_step(parent=check_shuffle_failures,
                  child=check_shuffle_service_kill)
    # Check if GC pause happened on the cluster
    check_if_gc_pause_happened = CheckGCPause()
    self.add_step(
        parent=check_shuffle_failures,
        child=check_if_gc_pause_happened,
    )
    # Check YarnRuntimeException
    check_yarn_runtime = CheckYarnRuntimeException()
    self.add_step(parent=check_shuffle_failures, child=check_yarn_runtime)
    # Check Job Throttling messages
    check_job_throttling = CheckJobThrottling()
    self.add_step(parent=check_shuffle_failures, child=check_job_throttling)
    # Check GCS Connector
    check_gcs_connector = CheckGCSConnector()
    self.add_step(parent=check_shuffle_failures, child=check_gcs_connector)
    #Check BQ Connector
    check_bq_connector = CheckBQConnector()
    self.add_step(parent=check_shuffle_failures, child=check_bq_connector)
    # Ending your runbook
    self.add_end(SparkJobEnd())


class JobExists(runbook.StartStep):
  """Prepares the parameters required for the dataproc/spark_job_failures runbook.

  Ensures both project_id, region and job_id parameters are available.
  """

  template = 'job::job_id_exists'

  def execute(self):
    """Verify job exists in Dataproc UI."""
    project = crm.get_project(op.get(flags.PROJECT_ID))

    if not op.get(flags.DATAPROC_JOB_ID) or not op.get(flags.REGION):
      op.add_failed(
          project,
          reason=op.prep_msg(
              op.FAILURE_REASON,
              project_id=project,
              job_id=op.get(flags.DATAPROC_JOB_ID),
              cluster_name=op.get(flags.DATAPROC_CLUSTER_NAME),
          ),
          remediation=op.prep_msg(op.FAILURE_REMEDIATION),
      )
      return

    # uses the API to get the cluster information from the job id
    try:
      job = dataproc.get_job_by_jobid(project_id=op.get(flags.PROJECT_ID),
                                      region=op.get(flags.REGION),
                                      job_id=op.get(flags.DATAPROC_JOB_ID))
    except (AttributeError, GcpApiError, IndexError, TypeError,
            ValueError) as e:
      op.put(flags.JOB_EXIST, 'false')
      op.add_failed(
          project,
          reason=op.prep_msg(
              op.FAILURE_REASON,
              project_id=project,
              job_id=op.get(flags.DATAPROC_JOB_ID),
              cluster_name=op.get(flags.DATAPROC_CLUSTER_NAME),
              error=e,
          ),
          remediation=op.prep_msg(op.FAILURE_REMEDIATION),
      )
      return

    # Start date is the date for when the job was running
    start_time = datetime.strptime(
        job.status_history['RUNNING'],
        '%Y-%m-%dT%H:%M:%S.%fZ').replace(tzinfo=timezone.utc)

    # End date is the start date + 7 days
    end_time = start_time + timedelta(days=7)

    # Saving cluster parameters
    op.put(flags.START_TIME, start_time)
    op.info(f'Start time utc:{start_time}')
    op.put(flags.END_TIME, end_time)
    op.info(f'End time utc:{end_time}')
    op.put(flags.CLUSTER_UUID, job.cluster_uuid)
    op.put(flags.DATAPROC_CLUSTER_NAME, job.cluster_name)

    if check_datetime_gap(op.get(flags.START_TIME), op.get(flags.END_TIME), 30):
      op.put(flags.JOB_OLDER_THAN_30_DAYS, True)
    else:
      op.put(flags.JOB_OLDER_THAN_30_DAYS, False)

    op.add_ok(
        project,
        reason=op.prep_msg(
            op.SUCCESS_REASON,
            project_id=project,
            job_id=op.get(flags.DATAPROC_JOB_ID),
            cluster_name=op.get(flags.DATAPROC_CLUSTER_NAME),
        ),
    )
    return


class DataProcClusterExists(runbook.Step):
  """Verify if cluster exists in Dataproc UI."""

  template = 'job::cluster_exists'

  def execute(self):
    """Verify cluster exists in Dataproc UI."""

    project = crm.get_project(op.get(flags.PROJECT_ID))

    if op.get(flags.JOB_EXIST) == 'false':
      op.add_skipped(project, reason="Job doesn't exist, skipping this step.")
      return

    cluster = dataproc.get_cluster(cluster_name=op.get(
        flags.DATAPROC_CLUSTER_NAME),
                                   region=op.get(flags.REGION),
                                   project=op.get(flags.PROJECT_ID))

    if cluster:
      op.put(flags.DATAPROC_CLUSTER_NAME, cluster.name)
      if not op.get(flags.SERVICE_ACCOUNT):
        #Saving Service Account parameter
        if cluster.vm_service_account_email:
          op.put(flags.SERVICE_ACCOUNT, cluster.vm_service_account_email)

      op.add_ok(
          cluster,
          reason=op.prep_msg(
              op.SUCCESS_REASON,
              cluster_name=cluster.name,
              project_id=project,
          ),
      )
    else:
      op.add_failed(
          cluster,
          reason=op.prep_msg(
              op.FAILURE_REASON,
              cluster_name=op.get(flags.DATAPROC_CLUSTER_NAME),
              project_id=project,
          ),
          remediation=op.prep_msg(op.FAILURE_REMEDIATION),
      )


class CheckStackdriverSetting(runbook.Step):
  """Check if Stackdriver is enabled for the cluster.

  If the property is provided manually, It will be used if
  the cluster does not exist.
  """

  template = 'dataproc_attributes::stackdriver'

  def execute(self):
    """Checking Stackdriver setting."""
    # taking cluster details
    cluster = dataproc.get_cluster(cluster_name=op.get(
        flags.DATAPROC_CLUSTER_NAME),
                                   region=op.get(flags.REGION),
                                   project=op.get(flags.PROJECT_ID))

    if cluster is not None:
      op.put(flags.STACKDRIVER, cluster.is_stackdriver_logging_enabled)

    if op.get(flags.STACKDRIVER):
      op.add_ok(cluster, reason=op.prep_msg(op.SUCCESS_REASON))
    else:
      op.add_uncertain(
          cluster,
          reason=op.prep_msg(op.UNCERTAIN_REASON),
          remediation=op.prep_msg(op.UNCERTAIN_REMEDIATION),
      )


class CheckClusterVersion(runbook.Step):
  """Verify if the cluster version is supported.
  """

  template = 'dataproc_attributes::unspported_image_version'

  def execute(self):
    """Verify cluster version."""

    supported_versions = dataproc.extract_dataproc_supported_version()
    cluster = dataproc.get_cluster(cluster_name=op.get(
        flags.DATAPROC_CLUSTER_NAME),
                                   region=op.get(flags.REGION),
                                   project=op.get(flags.PROJECT_ID))

    # If cluster cannot be found, gather details from flags
    if cluster is None:
      image_version = op.get(flags.IMAGE_VERSION)
      if image_version is None:
        op.add_skipped(
            cluster,
            'The cluster cannot be found, skipping this step. ' +
            'Please provide image_version as input parameter ' +
            'if the cluster is deleted or keep the cluster in error state.',
        )
      return

    image_version = '.'.join(cluster.image_version.split('.')[:2])
    op.put(flags.IMAGE_VERSION, image_version)

    if image_version in supported_versions:
      op.add_ok(
          cluster,
          reason=op.prep_msg(op.SUCCESS_REASON,
                             cluster_name=op.get(flags.DATAPROC_CLUSTER_NAME)),
      )
    else:
      op.add_failed(
          cluster,
          reason=op.prep_msg(op.FAILURE_REASON,
                             cluster_name=op.get(flags.DATAPROC_CLUSTER_NAME)),
          remediation=op.prep_msg(op.FAILURE_REMEDIATION),
      )


class CheckIfJobFailed(runbook.Step):
  """Verify if dataproc job failed."""

  template = 'job::job_failed'

  def execute(self):
    """Verify if job failed."""
    project = crm.get_project(op.get(flags.PROJECT_ID))
    if op.get(flags.JOB_EXIST) == 'false':
      op.add_skipped(project, reason="Job doesn't exist, skipping this step.")
      return

    job = dataproc.get_job_by_jobid(op.get(flags.PROJECT_ID),
                                    op.get(flags.REGION),
                                    op.get(flags.DATAPROC_JOB_ID))

    if job.state == 'DONE':
      op.add_failed(
          job,
          reason=op.prep_msg(op.FAILURE_REASON,
                             job_id=op.get(flags.DATAPROC_JOB_ID)),
          remediation=op.prep_msg(op.FAILURE_REMEDIATION),
      )
    else:
      op.add_ok(
          job,
          reason=op.prep_msg(op.SUCCESS_REASON,
                             job_id=op.get(flags.DATAPROC_JOB_ID)),
      )


class CheckTaskNotFound(runbook.CompositeStep):
  """Verify if dataproc job failed due to task not found."""

  template = 'job::task_not_found'

  def execute(self):
    """Verify if job didn't failed with 'task not found' error."""
    project = crm.get_project(op.get(flags.PROJECT_ID))

    if op.get(flags.JOB_EXIST) == 'false':
      op.add_skipped(project, reason="Job doesn't exist, skipping this step.")
      return

    if op.get(flags.JOB_OLDER_THAN_30_DAYS):
      op.add_skipped(
          project,
          reason=('Job is older than 30 days, skipping this step. '
                  'Please create a new job and run the runbook again.'),
      )
      return

    job = dataproc.get_job_by_jobid(op.get(flags.PROJECT_ID),
                                    op.get(flags.REGION),
                                    op.get(flags.DATAPROC_JOB_ID))

    cluster_uuid = job.cluster_uuid
    start_time = op.get(flags.START_TIME)
    end_time = op.get(flags.END_TIME)

    additional_message = (
        f'Unable to find the cluster deletion log between'
        f' {start_time} and {end_time}. It could be some other issue.'
        f'Please raise a support case to investigate further.')

    log_search_filter = f"""resource.type="cloud_dataproc_cluster"
    resource.labels.cluster_uuid="{cluster_uuid}"
    protoPayload.methodName="google.cloud.dataproc.v1.ClusterController.DeleteCluster"
    """

    log_entries = logs.realtime_query(
        project_id=op.get(flags.PROJECT_ID),
        filter_str=log_search_filter,
        start_time=start_time,
        end_time=end_time,
    )

    if log_entries:
      last_log = log_entries.pop()
      user = last_log['protoPayload']['authenticationInfo']['principalEmail']
      additional_message = f'User {user} deleted the cluster.'

    if job.details != 'Task not found':
      op.add_ok(
          job,
          reason=op.prep_msg(
              op.SUCCESS_REASON,
              job_id=op.get(flags.DATAPROC_JOB_ID),
              additional_message=additional_message,
          ),
      )
    else:
      op.add_failed(
          job,
          reason=op.prep_msg(
              op.FAILURE_REASON,
              job_id=op.get(flags.DATAPROC_JOB_ID),
              additional_message=additional_message,
          ),
          remediation=op.prep_msg(op.FAILURE_REMEDIATION),
      )


class CheckPermissions(runbook.CompositeStep):
  """Check if the permissions are set correctly.
  """

  template = 'permissions::permission_check'

  def execute(self):
    """Verify permissions ."""

    sa_email = op.get(flags.SERVICE_ACCOUNT)
    project = crm.get_project(op.get(flags.PROJECT_ID))
    op.info(('Service Account:{}').format(sa_email))

    if sa_email:
      sa_exists = iam.is_service_account_existing(email=sa_email,
                                                  billing_project_id=op.get(
                                                      flags.PROJECT_ID))
      sa_exists_cross_project = iam.is_service_account_existing(
          email=sa_email, billing_project_id=op.get(flags.CROSS_PROJECT_ID))
    else:
      sa_exists = False
      sa_exists_cross_project = False

    if sa_exists:
      op.info(
          'VM Service Account associated with Dataproc cluster was found in the'
          ' same project')
      op.info('Checking permissions.')
      # Check for Service Account permissions
      sa_permission_check = iam_gs.IamPolicyCheck()
      sa_permission_check.project = op.get(flags.PROJECT_ID)
      sa_permission_check.principal = (
          f'serviceAccount:{op.get(flags.SERVICE_ACCOUNT)}')
      sa_permission_check.require_all = True
      sa_permission_check.roles = ['roles/dataproc.worker']
      self.add_child(child=sa_permission_check)
    elif sa_exists_cross_project:
      op.info('VM Service Account associated with Dataproc cluster was found in'
              ' cross project')
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
          f'serviceAccount:{op.get(flags.SERVICE_ACCOUNT)}')
      sa_permission_check.require_all = True
      sa_permission_check.roles = [
          'roles/iam.serviceAccountUser',
          'roles/dataproc.worker',
      ]
      self.add_child(child=sa_permission_check)

      # Check Service Agent Service Account roles
      op.info('Checking service agent service account roles on service account'
              ' project.')
      # project = crm.get_project(op.get(flags.PROJECT_ID))
      service_agent_sa = (
          f'service-{project.number}@dataproc-accounts.iam.gserviceaccount.com')
      service_agent_permission_check = iam_gs.IamPolicyCheck()
      service_agent_permission_check.project = op.get(flags.CROSS_PROJECT_ID)
      service_agent_permission_check.principal = (
          f'serviceAccount:{service_agent_sa}')
      service_agent_permission_check.require_all = True
      service_agent_permission_check.roles = [
          'roles/iam.serviceAccountUser',
          'roles/iam.serviceAccountTokenCreator',
      ]
      self.add_child(child=service_agent_permission_check)

      # Check Compute Agent Service Account
      op.info('Checking compute agent service account roles on service account'
              ' project.')
      compute_agent_sa = (
          f'service-{project.number}@compute-system.iam.gserviceaccount.com')
      compute_agent_permission_check = iam_gs.IamPolicyCheck()
      compute_agent_permission_check.project = op.get(flags.CROSS_PROJECT_ID)
      compute_agent_permission_check.principal = (
          f'serviceAccount:{compute_agent_sa}')
      compute_agent_permission_check.require_all = True
      compute_agent_permission_check.roles = [
          'roles/iam.serviceAccountTokenCreator'
      ]
      self.add_child(child=compute_agent_permission_check)

    else:
      op.add_failed(project,
                    reason=op.prep_msg(op.FAILURE_REASON,
                                       service_account=op.get(
                                           flags.SERVICE_ACCOUNT),
                                       project_id=op.get(flags.PROJECT_ID)),
                    remediation=op.prep_msg(op.FAILURE_REMEDIATION))


class CheckMasterOOM(runbook.Step):
  """Check if OOM has happened on master.
  """

  template = 'logs_related::master_oom'

  def execute(self):
    """Verify if OOM has happened on master ."""

    project = crm.get_project(op.get(flags.PROJECT_ID))

    cluster_name = op.get(flags.DATAPROC_CLUSTER_NAME)
    cluster_uuid = op.get(flags.CLUSTER_UUID)
    job_id = op.get(flags.DATAPROC_JOB_ID)
    log_message = 'Task Not Acquired'

    log_search_filter = f"""resource.type="cloud_dataproc_cluster"
    resource.labels.cluster_name="{cluster_name}"
    resource.labels.cluster_uuid="{cluster_uuid}"
    "{job_id}"
    jsonPayload.message=~"{log_message}" """

    start_time = op.get(flags.START_TIME)
    end_time = op.get(flags.END_TIME)

    log_entries = logs.realtime_query(
        project_id=op.get(flags.PROJECT_ID),
        filter_str=log_search_filter,
        start_time=start_time,
        end_time=end_time,
    )

    if log_entries:
      log_message_check_sigterm = (
          'Driver received SIGTERM/SIGKILL signal and exited with')

      log_search_filter_check_sigterm = f"""resource.type="cloud_dataproc_cluster"
      resource.labels.cluster_name="{cluster_name}"
      resource.labels.cluster_uuid="{cluster_uuid}"
      "{job_id}"
      jsonPayload.message=~"{log_message_check_sigterm}" """

      log_entries_check_sigterm = logs.realtime_query(
          project_id=op.get(flags.PROJECT_ID),
          filter_str=log_search_filter_check_sigterm,
          start_time=start_time,
          end_time=end_time,
      )

      if log_entries_check_sigterm:
        op.add_failed(
            project,
            reason=op.prep_msg(
                op.FAILURE_REASON,
                log=log_message,
                cluster_name=cluster_name,
            ),
            remediation=op.prep_msg(op.FAILURE_REMEDIATION),
        )
        return
      else:
        log_message_check_yarn_metrics = (
            'Exception calling Future.get() on YARN metrics rpc')

        log_search_filter_check_yarn_metrics = f"""resource.type="cloud_dataproc_cluster"
        resource.labels.cluster_name="{cluster_name}"
        resource.labels.cluster_uuid="{cluster_uuid}"
        jsonPayload.message=~"{log_message_check_yarn_metrics}" """

        log_entries_check_yarn_metrics = logs.realtime_query(
            project_id=op.get(flags.PROJECT_ID),
            filter_str=log_search_filter_check_yarn_metrics,
            start_time=start_time,
            end_time=end_time,
        )
        if log_entries_check_yarn_metrics:
          op.add_failed(
              project,
              reason=op.prep_msg(
                  op.FAILURE_REASON,
                  cluster_name=cluster_name,
              ),
              remediation=op.prep_msg(op.FAILURE_REMEDIATION),
          )
          return

    op.add_ok(
        project,
        reason=op.prep_msg(
            op.SUCCESS_REASON,
            cluster_name=cluster_name,
        ),
    )


class CheckWorkerOOM(runbook.Step):
  """Verify if OOM has happened on worker nodes."""

  template = 'logs_related::worker_oom'

  def execute(self):
    """Verify if OOM has happened on worker nodes."""
    check_worker_oom = dp_gs.CheckLogsExist()
    check_worker_oom.template = self.template
    check_worker_oom.log_message = (
        '(Container exited with a non-zero exit code 143| Container exited with'
        ' a non-zero exit code 137|java.lang.OutOfMemoryError)')


class CheckSWPreemption(runbook.CompositeStep):
  """Verify if secondary worker preemption has happened."""

  template = 'logs_related::sw_preemption'

  def execute(self):
    """Check if secondary worker preemption has happened."""
    check_sw_preemption_log = dp_gs.CheckLogsExist()
    check_sw_preemption_log.template = self.template
    check_sw_preemption_log.log_message = dp_const.SW_PREEMPTION_LOG
    self.add_child(child=check_sw_preemption_log)


class CheckWorkerDiskUsageIssue(runbook.CompositeStep):
  """Verify if worker disk usage issue has happened."""

  template = 'logs_related::woker_disk_usage'

  def execute(self):
    """Check if secondary worker preemption has happened."""
    check_worker_disk_usage_log = dp_gs.CheckLogsExist()
    check_worker_disk_usage_log.template = self.template
    check_worker_disk_usage_log.log_message = dp_const.WORKER_DISK_USAGE_LOG
    self.add_child(child=check_worker_disk_usage_log)


class CheckPortExhaustion(runbook.CompositeStep):
  """Verify if the port exhaustion has happened."""

  template = 'logs_related::port_exhaustion'

  def execute(self):
    """Verify if the port exhaustion has happened."""

    project = crm.get_project(op.get(flags.PROJECT_ID))
    if op.get(flags.JOB_EXIST) == 'false':
      op.add_skipped(project, reason="Job doesn't exist, skipping this step.")
      return

    check_port_exhaustion_log = dp_gs.CheckLogsExist()
    check_port_exhaustion_log.template = 'logs_related::port_exhaustion'
    check_port_exhaustion_log.log_message = dp_const.PORT_EXHAUSTION_LOG
    self.add_child(child=check_port_exhaustion_log)


class CheckKillingOrphanedApplication(runbook.CompositeStep):
  """Verify if the killing of Orphaned applications has happened."""

  template = 'logs_related::kill_orphaned_application'

  def execute(self):
    """Verify if the killing of Orphaned applications has happened."""

    project = crm.get_project(op.get(flags.PROJECT_ID))
    if op.get(flags.JOB_EXIST) == 'false':
      op.add_skipped(project, reason="Job doesn't exist, skipping this step.")
      return

    check_kill_orphaned_application = dp_gs.CheckLogsExist()
    check_kill_orphaned_application.template = (
        'logs_related::kill_orphaned_application')
    check_kill_orphaned_application.log_message = dp_const.KILL_ORPHANED_APP_LOG
    self.add_child(child=check_kill_orphaned_application)


class CheckPythonImportFailure(runbook.CompositeStep):
  """Check if the python import failure has happened."""

  def execute(self):
    """Check Python import failure."""

    project = crm.get_project(op.get(flags.PROJECT_ID))
    if op.get(flags.JOB_EXIST) == 'false':
      op.add_skipped(project, reason="Job doesn't exist, skipping this step.")
      return

    check_python_import = dp_gs.CheckLogsExist()
    check_python_import.template = 'logs_related::check_python_import_failure'
    check_python_import.log_message = dp_const.PYTHON_IMPORT_LOG
    self.add_child(child=check_python_import)

    cluster = dataproc.get_cluster(cluster_name=op.get(
        flags.DATAPROC_CLUSTER_NAME),
                                   region=op.get(flags.REGION),
                                   project=op.get(flags.PROJECT_ID))

    if cluster:
      if cluster.initialization_actions:
        op.info(
            'The cluster has initialization actions. Please open a support case'
            ' and share more information of packages and versions of libraries'
            ' being fetched in your custom initialization actions scripts.')


class CheckShuffleFailures(runbook.Step):
  """Check for logs indicating shuffle failures."""

  template = 'logs_related::shuffle_failures'

  def execute(self):
    """Check for logs indicating shuffle failures."""

    project = crm.get_project(op.get(flags.PROJECT_ID))

    cluster_name = op.get(flags.DATAPROC_CLUSTER_NAME)
    cluster_uuid = op.get(flags.CLUSTER_UUID)

    log_search_filter = f"""resource.type="cloud_dataproc_cluster"
    resource.labels.cluster_name="{cluster_name}"
    resource.labels.cluster_uuid="{cluster_uuid}"
    "{op.get(flags.DATAPROC_JOB_ID)}"
    (
      ("ExecutorLostFailure" AND "Unable to create executor" AND "Unable to register with external shuffle server") OR
      ("java.io.IOException" AND "Exception while uploading shuffle data") OR
      ("Requesting driver to remove executor" AND "Container from a bad node")
    ) """

    if op.get(flags.JOB_OLDER_THAN_30_DAYS):
      op.add_skipped(
          project,
          reason=('Job is older than 30 days, skipping this step. '
                  'Please create a new job and run the runbook again.'),
      )
      return

    start_time = op.get(flags.START_TIME)
    end_time = op.get(flags.END_TIME)

    log_entries = logs.realtime_query(
        project_id=project.id,
        filter_str=log_search_filter,
        start_time=start_time,
        end_time=end_time,
    )

    if log_entries:
      cluster = dataproc.get_cluster(cluster_name=op.get(
          flags.DATAPROC_CLUSTER_NAME),
                                     region=op.get(flags.REGION),
                                     project=op.get(flags.PROJECT_ID))

      root_causes = []
      remediation = []

      # Check for insufficient primary workers in EFM
      if (cluster.config.software_config.properties.get(
          'dataproc:dataproc.enable.enhanced.flexibility.mode',
          'false') == 'true'):
        if (cluster.number_of_primary_workers /
            cluster.number_of_secondary_workers < 1):
          root_causes.append('Insufficient primary workers in EFM.')
          remediation.append(
              'Consider increasing the primary to secondary worker ratio.')

      # Check for older image and suggest EFM HCFS mode
      if (cluster.config.software_config.image_version.startswith('1.5') and
          cluster.config.software_config.properties.get(
              'dataproc:efm.spark.shuffle') != 'hcfs'):
        remediation.append(
            'Consider using EFM HCFS mode with GCS for older images.')

      # Check for small disk size
      disk_size_gb = cluster.config.worker_config.disk_config.boot_disk_size_gb
      if disk_size_gb < 500:
        root_causes.append(
            f'Small disk size ({disk_size_gb} GB) on cluster nodes.')
        remediation.append(
            'Consider increasing disk size for better I/O performance.')

      # Check for low IO connection timeout
      spark_shuffle_io_timeout = cluster.config.software_config.properties.get(
          'spark:spark.shuffle.io.connectionTimeout', 120)
      if spark_shuffle_io_timeout < 600:
        root_causes.append('Low IO connection timeout in Spark shuffle.')
        remediation.append(
            "Consider increasing 'spark:spark.shuffle.io.connectionTimeout' to"
            ' 600.')

      # Check for data skew and large partitions with PVM secondary workers
      if cluster.is_preemptible_secondary_workers:
        root_causes.append(
            'Data skew and large partitions might be an issue with PVM'
            ' secondary workers.')
        remediation.append(
            'Consider using smaller batches, increasing partition count, or'
            ' using a better partitioning key.')

      op.add_failed(
          crm.get_project(project.id),
          reason=op.prep_msg(
              op.FAILURE_REASON,
              cluster_name=cluster_name,
              root_causes=', '.join(root_causes),
          ),
          remediation=op.prep_msg(op.FAILURE_REMEDIATION,
                                  remediation=', '.join(remediation)),
      )
    else:
      op.add_ok(
          crm.get_project(project.id),
          reason=op.prep_msg(
              op.SUCCESS_REASON,
              cluster_name=cluster_name,
          ),
      )


class CheckShuffleServiceKill(runbook.CompositeStep):
  """Verify the presence of shuffle service kill related logs.
  """

  def execute(self):
    """Check Shuffle Service Kill logs and autoscaling & preemptibility."""

    project = crm.get_project(op.get(flags.PROJECT_ID))
    if op.get(flags.JOB_EXIST) == 'false':
      op.add_skipped(project, reason="Job doesn't exist, skipping this step.")
      return

    check_shuffle_kill = dp_gs.CheckLogsExist()
    check_shuffle_kill.template = 'logs_related::shuffle_service_kill'
    check_shuffle_kill.log_message = dp_const.SHUFFLE_KILL_LOG
    self.add_child(child=check_shuffle_kill)
    self.add_child(child=CheckAutoscalingPolicy())


class CheckAutoscalingPolicy(runbook.Step):
  """Verify autoscaling policies."""

  template = 'logs_related::shuffle_service_kill_graceful_decommision_timeout'

  def execute(self):
    """Checking autoscaling policies and graceful decommission timeouts."""

    project = crm.get_project(op.get(flags.PROJECT_ID))
    cluster = dataproc.get_cluster(
        cluster_name=op.get(flags.DATAPROC_CLUSTER_NAME),
        region=op.get(flags.REGION),
        project=op.get(flags.PROJECT_ID),
    )

    if cluster:
      autoscaling_policy_id = cluster.autoscaling_policy_id
      if autoscaling_policy_id:
        policy = dataproc.get_auto_scaling_policy(
            project.id,
            op.get(flags.REGION),
            cluster.autoscaling_policy_id,
        )
        if not policy.has_graceful_decommission_timeout:
          op.add_failed(
              project,
              reason=op.prep_msg(op.FAILURE_REASON,
                                 cluster_name=op.get(
                                     flags.DATAPROC_CLUSTER_NAME)),
              remediation=op.prep_msg(op.FAILURE_REMEDIATION),
          )
        else:
          op.add_ok(
              project,
              reason=op.prep_msg(
                  op.SUCCESS_REASON,
                  cluster_name=op.get(flags.DATAPROC_CLUSTER_NAME),
              ),
          )


class CheckPreemptible(runbook.Step):
  """Verify preemptibility."""

  template = 'logs_related::shuffle_service_kill_preemptible_workers'

  def execute(self):
    """Checking worker count."""

    project = crm.get_project(op.get(flags.PROJECT_ID))
    cluster = dataproc.get_cluster(cluster_name=op.get(
        flags.DATAPROC_CLUSTER_NAME),
                                   region=op.get(flags.REGION),
                                   project=op.get(flags.PROJECT_ID))

    total_worker_count = (cluster.number_of_primary_workers +
                          cluster.number_of_secondary_workers)
    preemptible_worker_count = (cluster.number_of_primary_workers if
                                cluster.is_preemptible_primary_workers else 0)
    preemptible_worker_count += (cluster.number_of_secondary_workers
                                 if cluster.is_preemptible_secondary_workers
                                 else 0)

    if preemptible_worker_count > 0:
      if preemptible_worker_count / total_worker_count >= 0.5:
        op.add_failed(
            project,
            reason=op.prep_msg(op.FAILURE_REASON,
                               cluster_name=op.get(
                                   flags.DATAPROC_CLUSTER_NAME)),
            remediation=op.prep_msg(op.FAILURE_REMEDIATION),
        )
      else:
        op.add_ok(
            project,
            reason=op.prep_msg(op.SUCCESS_REASON,
                               cluster_name=op.get(
                                   flags.DATAPROC_CLUSTER_NAME)),
        )


class CheckGCPause(runbook.CompositeStep):
  """Verify if STW GC Pause has happened."""

  template = 'logs_related::gc_pause'

  def execute(self):
    """Check if STW GC Pause has happened on the cluster."""
    check_gc_pause = dp_gs.CheckLogsExist()
    check_gc_pause.template = 'logs_related::gc_pause'
    check_gc_pause.log_message = dp_const.GC_PAUSE_LOG
    self.add_child(child=check_gc_pause)


class CheckJobThrottling(runbook.CompositeStep):
  """Verify the presence of Job Throttling logs."""

  def execute(self):
    """Check for Job Throttling messages in the logs."""

    # Check "Too many running jobs"
    too_many_jobs = dp_gs.CheckLogsExist()
    too_many_jobs.template = 'logs_related::too_many_jobs'
    too_many_jobs.log_message = dp_const.TOO_MANY_JOBS_LOG
    self.add_child(child=too_many_jobs)

    # Check "Not enough free memory"
    not_enough_memory = dp_gs.CheckLogsExist()
    not_enough_memory.template = 'logs_related::not_enough_memory'
    not_enough_memory.log_message = dp_const.NOT_ENOUGH_MEMORY_LOG
    self.add_child(child=not_enough_memory)

    # Check "High system memory usage"
    system_memory = dp_gs.CheckLogsExist()
    system_memory.template = 'logs_related::system_memory'
    system_memory.log_message = dp_const.SYSTEM_MEMORY_LOG
    self.add_child(child=system_memory)

    # Check "Rate limit"
    rate_limit = dp_gs.CheckLogsExist()
    rate_limit.template = 'logs_related::rate_limit'
    rate_limit.log_message = dp_const.RATE_LIMIT_LOG
    self.add_child(child=rate_limit)

    # Check "Master agent not initialized"
    not_initialized = dp_gs.CheckLogsExist()
    # not_initialized.template = 'logs_related::not_initialized'
    not_initialized.log_message = dp_const.NOT_INITIALIZED_LOG
    self.add_child(child=not_initialized)

    # Check "Disk space too low on Master"
    not_enough_disk = dp_gs.CheckLogsExist()
    not_enough_disk.template = 'logs_related::not_enough_disk'
    not_enough_disk.log_message = dp_const.NOT_ENOUGH_DISK_LOG
    self.add_child(child=not_enough_disk)


class CheckYarnRuntimeException(runbook.CompositeStep):
  """Verify presence of CheckYarnRuntimeException logs."""

  def execute(self):
    """Check for CheckYarnRuntimeException logs."""
    yarn_runtime = dp_gs.CheckLogsExist()
    yarn_runtime.template = 'logs_related::yarn_runtime'
    yarn_runtime.log_message = dp_const.YARN_RUNTIME_LOG
    self.add_child(child=yarn_runtime)


# Check if cx is using a non-default GCS connector:
class CheckGCSConnector(runbook.CompositeStep):
  """Check for non-default GCS connector and for errors in logs connected to Cloud Storage."""

  template = 'dataproc_attributes::gcs_connector'

  def execute(self):
    """Check for non-default GCS connector."""
    cluster = dataproc.get_cluster(cluster_name=op.get(
        flags.DATAPROC_CLUSTER_NAME),
                                   region=op.get(flags.REGION),
                                   project=op.get(flags.PROJECT_ID))

    # Checks if a cx provided value for GCS connector exists
    if cluster is not None:
      if cluster.is_custom_gcs_connector:
        op.add_uncertain(
            cluster,
            reason=op.prep_msg(op.UNCERTAIN_REASON),
            remediation=op.prep_msg(op.UNCERTAIN_REMEDIATION),
        )

      else:
        op.add_ok(cluster, reason=op.prep_msg(op.SUCCESS_REASON))

    # Check 403 error
    check_gcs_forbidden = dp_gs.CheckLogsExist()
    check_gcs_forbidden.template = 'logs_related::gcs_access_deny'
    check_gcs_forbidden.log_message = dp_const.ERROR_403_LOG
    self.add_child(child=check_gcs_forbidden)

    # Check 429 error due to GCE
    check_429_gce = dp_gs.CheckLogsExist()
    check_429_gce.template = 'logs_related::gcs_429_gce'
    check_429_gce.log_message = dp_const.ERROR_429_GCE_LOG
    self.add_child(child=check_429_gce)

    # Check 429 error connected to driver output
    check_429_driveroutput = dp_gs.CheckLogsExist()
    check_429_driveroutput.template = 'logs_related::gcs_429_driveroutput'
    check_429_driveroutput.log_message = dp_const.ERROR_429_DRIVER_LOG
    self.add_child(child=check_429_driveroutput)

    # Check 412 error
    check_412 = dp_gs.CheckLogsExist()
    check_412.template = 'logs_related::gcs_412'
    check_412.log_message = dp_const.ERROR_412_LOG
    self.add_child(child=check_412)


class CheckBQConnector(runbook.CompositeStep):
  """Check for issues related to BigQuery connector such as version dependency conflicts."""

  template = 'dataproc_attributes::bq_connector'

  def execute(self):
    """Check if non-default BigQuery connector version exists."""
    cluster = dataproc.get_cluster(cluster_name=op.get(
        flags.DATAPROC_CLUSTER_NAME),
                                   region=op.get(flags.REGION),
                                   project=op.get(flags.PROJECT_ID))
    job = dataproc.get_job_by_jobid(project_id=op.get(flags.PROJECT_ID),
                                    region=op.get(flags.REGION),
                                    job_id=op.get(flags.DATAPROC_JOB_ID))

    if cluster is not None:
      if version.parse(op.get(flags.IMAGE_VERSION)) > version.parse('2.0'):
        # op.info('Cluster higher than 2.0')
        # Extract BQ version from Dataproc Version page:
        bq_version = dataproc.extract_dataproc_bigquery_version(
            op.get(flags.IMAGE_VERSION))
        if (not cluster.cluster_provided_bq_connector and
            not job.job_provided_bq_connector):
          op.add_ok(
              cluster,
              reason=op.prep_msg(op.SUCCESS_REASON,
                                 image_version=op.get(flags.IMAGE_VERSION)),
          )
        elif ((cluster.cluster_provided_bq_connector or
               job.job_provided_bq_connector) != bq_version) or (
                   cluster.cluster_provided_bq_connector or
                   job.job_provided_bq_connector == 'spark-bigquery-latest'):
          op.add_uncertain(
              cluster,
              reason=op.prep_msg(op.FAILURE_REASON,
                                 image_version=op.get(flags.IMAGE_VERSION)),
              remediation=op.prep_msg(
                  op.FAILURE_REMEDIATION,
                  image_version=op.get(flags.IMAGE_VERSION),
                  bq_version=bq_version,
              ),
          )
      # If image version <= 2.0
      else:
        if (cluster.cluster_provided_bq_connector or
            job.job_provided_bq_connector):
          op.add_ok(
              cluster,
              reason=op.prep_msg(op.SUCCESS_REASON,
                                 image_version=op.get(flags.IMAGE_VERSION)),
          )
        elif not (cluster.cluster_provided_bq_connector or
                  job.job_provided_bq_connector):
          op.add_skipped(cluster, reason='The BigQuery connector is not used.')

    else:
      op.add_skipped(cluster,
                     reason='Cluster does not exist, skipping this step.')

    check_bq_resource = dp_gs.CheckLogsExist()
    check_bq_resource.template = 'logs_related::bq_resource'
    check_bq_resource.log_message = dp_const.BQ_RESOURCE_LOG
    self.add_child(child=check_bq_resource)


class SparkJobEnd(runbook.EndStep):
  """The end step of the runbook.

  Points out all the failed steps to the user.
  """

  def execute(self):
    """This is the end step of the runbook."""
    op.info(
        """Please visit all the FAIL steps and address the suggested remediations.
        If the REMEDIATION suggestions were not able to solve your issue please open a Support case
        with failed job details:
          1. Driver output
          2. YARN application logs
          3. (optional) Event logs, if you are facing a performance issue
          4. (optional) If there was a successful run in the past,
          provide job id and logs of that run""")


def check_datetime_gap(date1, date2, gap_in_days):
  """Checks if two datetime objects are within a certain gap in days."""

  return (date2 - date1).days > gap_in_days
