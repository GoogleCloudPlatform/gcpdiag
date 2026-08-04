# Copyright 2026 Google LLC
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

"""Runbook for diagnosing Airflow Scheduler issues in Cloud Composer."""

from datetime import datetime

from gcpdiag import runbook, utils
from gcpdiag.queries import composer, iam, logs, monitoring
from gcpdiag.runbook import op
from gcpdiag.runbook.gce import flags


class SchedulerIssues(runbook.DiagnosticTree):
  """Runbook for diagnosing Airflow Scheduler health issues.

  This runbook investigates common causes for unhealthy Airflow schedulers:
  - High CPU utilization.
  - Missing deployments or deleted resources.
  - Service account issues.
  - Organization policy constraints.
  - Liveness probe failures.
  """

  parameters = {
    flags.PROJECT_ID: {
      'type': str,
      'help': 'The Project ID of the resource under investigation',
      'required': True,
    },
    flags.NAME: {
      'type': str,
      'help': 'The name of the Composer environment',
      'required': True,
    },
    flags.START_TIME: {
      'type': datetime,
      'help': 'Start time for log analysis (YYYY-MM-DDTHH:MM:SSZ).',
    },
    flags.END_TIME: {
      'type': datetime,
      'help': 'End time for log analysis (YYYY-MM-DDTHH:MM:SSZ).',
    },
  }

  def build_tree(self):
    """Construct the diagnostic tree with appropriate steps."""
    start = SchedulerIssuesStart()
    self.add_start(start)
    self.add_step(parent=start, child=SchedulerHealthCheck())
    self.add_step(parent=start, child=SchedulerLivenessProbeCheck())
    self.add_step(parent=start, child=SchedulerCPUUtilization())
    self.add_step(parent=start, child=CheckSchedulerExceededRuns())
    self.add_step(parent=start, child=CheckDeletedAirflowSchedulerDeployment())
    self.add_step(parent=start, child=DisabledEnvironmentServiceAccount())
    self.add_step(parent=start, child=DeletedEnvironmentServiceAccount())
    self.add_step(parent=start, child=SharedVpcOrgPolicyConstraint())


class SchedulerIssuesStart(runbook.StartStep):
  """Validates environment existence and extracts GKE metadata.

  Extracts environment name, GKE cluster name and service account from the
  Composer environment.
  """

  def execute(self):
    """Validate environment existence and extract GKE metadata.

    Extracts environment name, GKE cluster name and service account from the
    Composer environment.
    """
    project_id = op.get(flags.PROJECT_ID)
    env_name = op.get(flags.NAME)
    try:
      all_envs = composer.get_environments(op.get_context())
    except utils.GcpApiError as e:
      op.add_skipped(None, reason=f'Failed to get Composer environments: {e}')
      return
    selected_env = next((e for e in all_envs if e.name == env_name), None)

    if not selected_env:
      op.add_failed(
        resource=None,
        reason=(f'Composer environment "{env_name}" not found in project "{project_id}".'),
        remediation='Verify the environment name and project ID are correct.',
      )
      return
    gke_cluster_full = selected_env.gke_cluster
    cluster_name = gke_cluster_full.split('/')[-1]
    op.put('selected_env', selected_env)
    op.put('cluster_name', cluster_name)
    service_account = selected_env.service_account
    op.put('selected_service_account', service_account)
    op.add_ok(
      resource=selected_env,
      reason=(f'Found environment : {env_name} and GKE cluster : {cluster_name}'),
    )


class LogCheckStep(runbook.Step):
  """Base class for performing a log query and reporting results for a given step."""

  def run_query(self, filter_str):
    """Executes a log query and updates step status using template-defined messages.

    Args:
      filter_str: The filter string to use for the log query.

    Returns:
      True if the query returned results, False otherwise.
    """
    project_id = op.get(flags.PROJECT_ID)
    selected_env = op.get('selected_env')

    res = logs.realtime_query(
      project_id=project_id,
      filter_str=filter_str,
      start_time=op.get(flags.START_TIME),
      end_time=op.get(flags.END_TIME),
    )

    if res:
      op.add_failed(
        resource=selected_env,
        reason=op.prep_msg(op.FAILURE_REASON),
        remediation=op.prep_msg(op.FAILURE_REMEDIATION),
      )
      return True
    else:
      op.add_ok(resource=selected_env, reason=op.prep_msg(op.SUCCESS_REASON))


class SchedulerHealthCheck(runbook.Step):
  """Check the scheduler health via Monitoring.

  This step checks the scheduler heartbeat count to determine the scheduler
  health.
  """

  template = 'scheduler::check_scheduler_health'

  def execute(self):
    """Check the scheduler health via Monitoring."""
    project_id = op.get(flags.PROJECT_ID)
    env_name = op.get(flags.NAME)
    selected_env_resource = op.get('selected_env')

    scheduler_health_query = monitoring.query(
      project_id,
      """
          fetch cloud_composer_environment
          | metric 'composer.googleapis.com/environment/scheduler_heartbeat_count'
          | filter
              (resource.project_id == '{}'
              && resource.environment_name == '{}')
          | group_by 1m,
              [value_scheduler_heartbeat_count_mean:
                mean(value.scheduler_heartbeat_count)]
          | every 1m
          | group_by [resource.environment_name],
              [value_scheduler_heartbeat_count_mean_aggregate:
                mean(value_scheduler_heartbeat_count_mean)]
          | within 10m
          | filter val() > 0
          """.format(
        project_id,
        env_name,
      ),
    )
    if scheduler_health_query:
      op.add_ok(resource=selected_env_resource, reason=op.prep_msg(op.SUCCESS_REASON))
    else:
      op.add_failed(
        resource=selected_env_resource,
        reason=op.prep_msg(op.FAILURE_REASON),
        remediation=op.prep_msg(op.FAILURE_REMEDIATION),
      )


class SchedulerLivenessProbeCheck(LogCheckStep):
  """Check the liveness probe logs for the scheduler via Cloud Logging.

  This step checks the liveness probe logs for the scheduler to determine if
  the scheduler is healthy.
  """

  template = 'scheduler::check_liveness_probe'

  def execute(self):
    """Checks the liveness probe logs for the scheduler."""
    cluster = op.get('cluster_name')
    lql_filter = f"""
    resource.labels.cluster_name="{cluster}"
    resource.type="k8s_pod"
    "airflow-scheduler" AND "Liveness probe failed"
    """
    self.run_query(lql_filter)


class SchedulerCPUUtilization(runbook.Step):
  """Check the scheduler CPU utilization via Monitoring.

  This step checks the scheduler CPU utilization to determine if the scheduler
  is overloaded.
  """

  template = 'scheduler::check_scheduler_cpu_utilization'

  def execute(self):
    """Checks the scheduler CPU utilization."""
    cluster = op.get('cluster_name')
    selected_env = op.get('selected_env')
    num_schedulers = selected_env.num_schedulers
    cx_config_scheduler_cpu = selected_env.scheduler_cpu
    cpu_usage_threshold_scheduler = cx_config_scheduler_cpu * num_schedulers

    if cx_config_scheduler_cpu is None:
      op.add_skipped(
        resource=selected_env,
        reason=('Scheduler CPU configuration not found (e.g., Composer 1 environment).'),
      )
      return
    project_id = op.get(flags.PROJECT_ID)

    result = monitoring.query(
      project_id,
      """
          fetch k8s_container
          | metric 'kubernetes.io/container/cpu/core_usage_time'
          | filter
              (resource.cluster_name == '{}'
              && resource.pod_name =~ 'airflow-scheduler-.*')
          | align rate(1m)
          | every 1m
          | group_by [],
              [value_core_usage_time_aggregate: aggregate(value.core_usage_time)]
          | within 10m
          | filter val() >= {}
          """.format(cluster, cpu_usage_threshold_scheduler),
    )
    if result:
      op.add_failed(
        resource=selected_env,
        reason=op.prep_msg(op.FAILURE_REASON),
        remediation=op.prep_msg(op.FAILURE_REMEDIATION),
      )
    else:
      op.add_ok(resource=selected_env, reason=op.prep_msg(op.SUCCESS_REASON))


class CheckDeletedAirflowSchedulerDeployment(LogCheckStep):
  """Check the deleted airflow-scheduler deployment via Cloud Logging.

  This step checks the deleted airflow-scheduler deployment via Cloud Logging.
  """

  template = 'scheduler::check_deleted_airflow_scheduler_deployment'

  def execute(self):
    """Checks the deleted airflow-scheduler deployment."""
    cluster = op.get('cluster_name')
    lql_filter = f"""
    resource.labels.cluster_name="{cluster}"
    resource.type="gke_cluster"
    protoPayload.methodName="io.k8s.api.apps.v1.deployments.delete"
    protoPayload.resourceName:"deployments/airflow-scheduler"
    """
    self.run_query(lql_filter)


class CheckSchedulerExceededRuns(runbook.Step):
  """Check the scheduler exceeded 5,000 runs via Cloud Logging.

  This step checks the scheduler exceeded 5,000 runs via Cloud Logging.
  """

  template = 'scheduler::check_scheduler_exceeded_5000_runs'

  def execute(self):
    """Checks the scheduler exceeded 5,000 runs."""
    cluster = op.get('cluster_name')
    project_id = op.get(flags.PROJECT_ID)
    selected_env = op.get('selected_env')
    lql_filter = f"""
    resource.labels.cluster_name="{cluster}"
    resource.labels.container_name="airflow-scheduler"
    "Exiting scheduler loop as requested number of runs"
    """
    res = logs.realtime_query(
      project_id=project_id,
      filter_str=lql_filter,
      start_time=op.get(flags.START_TIME),
      end_time=op.get(flags.END_TIME),
    )
    if res:
      op.add_ok(
        resource=selected_env,
        reason=(op.prep_msg(op.FAILURE_REASON)),
      )
    else:
      op.add_ok(resource=selected_env, reason=op.prep_msg(op.SUCCESS_REASON))


class DisabledEnvironmentServiceAccount(runbook.Step):
  """Check the disabled/deleted environment service account via Cloud Logging.

  This step checks the disabled/deleted environment service account via Cloud
  Logging.
  """

  template = 'scheduler::check_disabled_deleted_environment_service_account'

  def execute(self):
    """Checks if the environment service account is disabled or deleted."""
    service_account = op.get('selected_service_account')
    selected_env = op.get('selected_env')

    if not iam.is_service_account_enabled(service_account, op.get_context()):
      op.add_failed(
        resource=selected_env,
        reason=op.prep_msg(op.FAILURE_REASON),
        remediation=op.prep_msg(op.FAILURE_REMEDIATION),
      )
    else:
      op.add_ok(resource=selected_env, reason=op.prep_msg(op.SUCCESS_REASON))


class DeletedEnvironmentServiceAccount(LogCheckStep):
  """Checks the deleted environment service account via Cloud Logging.

  This step checks the deleted environment service account via Cloud Logging.
  """

  template = 'scheduler::check_deleted_environment_service_account'

  def execute(self):
    """Checks the deleted environment service account."""
    service_account = op.get('selected_service_account')

    lql_filter = f"""
    resource.type="service_account"
    resource.labels.service_account_id="{service_account}"
    protoPayload.methodName="google.iam.admin.v1.DeleteServiceAccount"
    """
    self.run_query(lql_filter)


class SharedVpcOrgPolicyConstraint(LogCheckStep):
  """Check the shared VPC org policy constraint via Cloud Logging.

  This step checks the shared VPC org policy constraint via Cloud Logging.
  """

  template = 'scheduler::check_shared_vpc_org_policy_constraint'

  def execute(self):
    """Checks the shared VPC org policy constraint."""
    cluster = op.get('cluster_name')

    lql_filter = f"""
    resource.labels.cluster_name="{cluster}"
    (
      "Failed adding 1 nodes" AND
      "Org Policy constraint violated"
    )
    """
    self.run_query(lql_filter)
