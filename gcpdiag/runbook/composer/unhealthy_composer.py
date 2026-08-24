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
"""Runbook for diagnosing unhealthy Composer environments."""

from datetime import datetime

from gcpdiag import runbook, utils
from gcpdiag.queries import composer, iam, logs, monitoring
from gcpdiag.runbook import op
from gcpdiag.runbook.gce import flags


class UnhealthyComposer(runbook.DiagnosticTree):
  """Diagnose and troubleshoot unhealthy Composer environments.

  This runbook investigates common causes for an unhealthy status in a Cloud
  Composer environment by analyzing GKE health, resource utilization, and
  component logs.

  step 1 - Check environment health status
  step 2 - Check for GKE IP exhaustion
  step 3 - Validate environment service account status
  step 4 - Check plugins directory existence
  step 5 - Check web server CPU utilization
  step 6 - Check for monitoring pod restarts
  step 7 - Check for snapshot load pod restarts
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
      'help': 'The start time of the environment',
      'required': True,
    },
    flags.END_TIME: {
      'type': datetime,
      'help': 'The end time of the environment',
      'required': True,
    },
  }

  def build_tree(self):
    """Construct the diagnostic tree with appropriate steps."""
    start = UnhealthyComposerStart()
    self.add_start(start)
    monitoring_health_status = MonitoringHealthStatus()
    gke_ip_exhaustion = GkeIpExhaustion()
    service_account_status = ServiceAccountStatus()
    plugins_directory_check = PluginsDirectoryCheck()
    webserver_cpu_utilization = WebServerCpuUtilization()
    monitoring_stability = MonitoringStability()
    snapshot_load_stability = SnapshotLoadStability()

    self.add_step(parent=start, child=monitoring_health_status)
    self.add_step(parent=start, child=gke_ip_exhaustion)
    self.add_step(parent=start, child=service_account_status)
    self.add_step(parent=start, child=plugins_directory_check)
    self.add_step(parent=start, child=webserver_cpu_utilization)
    self.add_step(parent=start, child=monitoring_stability)
    self.add_step(parent=start, child=snapshot_load_stability)
    self.add_end(UnhealthyComposerEnd())


class UnhealthyComposerStart(runbook.StartStep):
  """Start step for the unhealthy Composer environment diagnostic tree.

  This step is used to find the Composer environment and check if it exists.
  """

  def execute(self):
    """Find the Composer environment and check if it exists in the project."""
    env_name = op.get(flags.NAME)
    project_id = op.get(flags.PROJECT_ID)

    op.info(f'Locating Composer environment "{env_name}" in project "{project_id}"...')
    try:
      all_envs = composer.get_environments(op.get_context())
    except utils.GcpApiError as e:
      op.add_skipped(None, reason=f'Failed to get Composer environments: {e}')
      return
    selected_env = next((e for e in all_envs if e.name == env_name), None)

    if not selected_env:
      op.add_failed(
        resource=None,
        reason=f'Composer environment "{env_name}" not found.',
        remediation='Verify the name and project ID are correct.',
      )
      return

    op.add_ok(
      resource=selected_env,
      reason=f'Environment "{env_name}" found in project "{project_id}".',
    )
    op.put('env', selected_env)
    op.put('project_id', project_id)
    env = op.get('env')
    gke_cluster_name = env.gke_cluster
    parts = gke_cluster_name.split('/')
    cluster_name = parts[-1]
    op.put('cluster_name', cluster_name)


class MonitoringHealthStatus(runbook.Step):
  """Check if Cloud Monitoring reports the environment as unhealthy.

  This step queries Cloud Monitoring to see if the environment has reported
  unhealthy for an extended period.
  """

  template = 'composer::health_metric'

  def execute(self):
    """Check environment health (Cloud Monitoring)."""
    env = op.get('env')
    project_id = op.get('project_id')
    try:
      result = monitoring.query(
        project_id,
        """
          fetch cloud_composer_environment
          | metric 'composer.googleapis.com/environment/healthy'
          | filter
              resource.project_id == '{}'
              && resource.environment_name == '{}'
          | align fraction_true_aligner(30m)
          """.format(project_id, env.name),
      )
    except utils.GcpApiError as e:
      op.add_skipped(env, reason=f'Failed to query monitoring metrics: {e}')
      return

    is_missing = not result
    has_zero = False
    if result:
      for ts in result.values():
        for val in ts['values']:
          if val[0] < 0.9:
            has_zero = True
            break
        if has_zero:
          break

    if is_missing or has_zero:
      op.add_failed(
        resource=env,
        reason=op.prep_msg(op.FAILURE_REASON, env_name=env.name),
        remediation=op.prep_msg(op.FAILURE_REMEDIATION),
      )
      return
    else:
      op.add_ok(resource=env, reason=op.prep_msg(op.SUCCESS_REASON, env_name=env.name))


class GkeIpExhaustion(runbook.Step):
  """Check if the GKE cluster has IP exhaustion.

  This step queries Cloud Logging to see if the GKE cluster has any IP
  exhaustion events.
  """

  template = 'composer::gke_ip_exhaustion'

  def execute(self):
    """Check if the GKE cluster has IP exhaustion issues."""
    start_time = op.get('start_time')
    end_time = op.get('end_time')
    env = op.get('env')
    project_id = op.get('project_id')
    cluster_name = op.get('cluster_name')
    try:
      ip_exhaustion_log_entries = logs.realtime_query(
        project_id=project_id,
        filter_str="""
          resource.type="k8s_cluster"
          resource.labels.cluster_name="{}"
          Search("IP_SPACE_EXHAUSTED")
          """.format(cluster_name),
        start_time=start_time,
        end_time=end_time,
      )
    except utils.GcpApiError as e:
      op.add_skipped(
        resource=env,
        reason=f'Failed to query IP exhaustion logs: {e}',
      )
      return
    if ip_exhaustion_log_entries:
      op.add_failed(
        resource=env,
        reason=op.prep_msg(
          op.FAILURE_REASON,
          gke_cluster=cluster_name,
        ),
        remediation=op.prep_msg(op.FAILURE_REMEDIATION),
      )
      return
    else:
      op.add_ok(
        resource=env,
        reason=op.prep_msg(
          op.SUCCESS_REASON,
          env_name=env.name,
          cluster_name=cluster_name,
        ),
      )


class ServiceAccountStatus(runbook.Step):
  """Check the status of the Composer environment's service accounts.

  This step queries the IAM API to see if the service accounts associated with
  the Composer environment exist.
  """

  template = 'composer::service_account_status'

  def execute(self):
    """Validate environment service account."""
    env = op.get('env')
    service_account = env.service_account
    op.put('selected_service_account', service_account)
    try:
      sa_exists = iam.is_service_account_existing(service_account, op.get_context())
    except utils.GcpApiError as e:
      op.add_skipped(
        resource=env,
        reason=f'Failed to check service accounts: {e}',
      )
      return
    if not sa_exists:
      op.add_failed(
        resource=env,
        reason=op.prep_msg(
          op.FAILURE_REASON,
          service_account=service_account,
        ),
        remediation=op.prep_msg(op.FAILURE_REMEDIATION),
      )
      return
    else:
      op.add_ok(
        resource=env,
        reason=op.prep_msg(
          op.SUCCESS_REASON,
          service_account=service_account,
        ),
      )


class PluginsDirectoryCheck(runbook.Step):
  """Check if the Composer environment's plugins directory exists.

  This step queries Cloud Logging to see if the environment has any logs
  indicating that the plugins directory is missing.
  """

  template = 'composer::plugins_directory_check'

  def execute(self):
    """Verify plugins directory."""
    start_time = op.get(flags.START_TIME)
    end_time = op.get(flags.END_TIME)
    env = op.get('env')
    project_id = op.get('project_id')
    try:
      plugin_missing_log_entries = logs.realtime_query(
        project_id=project_id,
        filter_str="""
          resource.type="cloud_composer_environment"
          resource.labels.environment_name="{}"
          Search("Plugins directory is missing in the bucket, not syncing.")
          """.format(env.name),
        start_time=start_time,
        end_time=end_time,
      )
    except utils.GcpApiError as e:
      op.add_skipped(
        resource=env,
        reason=f'Failed to query plugins directory logs: {e}',
      )
      return
    if plugin_missing_log_entries:
      op.add_failed(
        resource=env,
        reason=op.prep_msg(
          op.FAILURE_REASON,
          env_name=env.name,
        ),
        remediation=op.prep_msg(op.FAILURE_REMEDIATION),
      )
      return
    else:
      op.add_ok(
        resource=env,
        reason=op.prep_msg(
          op.SUCCESS_REASON,
          env_name=env.name,
        ),
      )


class WebServerCpuUtilization(runbook.Step):
  """Check the CPU utilization of the Composer environment's web server.

  This step queries the Kubernetes API to see if the web server pod has high
  CPU utilization.
  """

  template = 'composer::webserver_cpu_utilization'

  def execute(self):
    """Analyze web server CPU usage."""
    env = op.get('env')
    project_id = op.get('project_id')
    cluster_name = op.get('cluster_name')
    cpu_limit = env.webserver_cpu
    if cpu_limit is None:
      op.add_skipped(
        resource=env,
        reason='Web server CPU limit not found in environment config.',
      )
      return

    try:
      web_server_cpu_utilization = monitoring.query(
        project_id,
        """
          fetch k8s_container
            | metric 'kubernetes.io/container/cpu/core_usage_time'
            | filter
                resource.project_id == '{}'
                &&
                (resource.cluster_name == '{}'
                  && resource.pod_name =~ 'airflow-webserver-.*')
            | align rate(1m)
            | every 1m
            | group_by [],
                [value_core_usage_time_aggregate: aggregate(value.core_usage_time)]
          """.format(project_id, cluster_name),
      )
    except utils.GcpApiError as e:
      op.add_skipped(
        resource=env,
        reason=f'Failed to query web server CPU utilization: {e}',
      )
      return
    current_utilization = None

    for ts in web_server_cpu_utilization.values():
      if 'values' in ts and len(ts['values']) > 0 and len(ts['values'][0]) > 0:
        current_utilization = ts['values'][0][0]
        break
    if current_utilization is None:
      op.add_skipped(
        resource=env,
        reason=(f'No CPU utilization data found for cluster {cluster_name} webserver pods.'),
      )
      return
    if current_utilization < cpu_limit:
      op.add_ok(
        resource=env,
        reason=op.prep_msg(
          op.SUCCESS_REASON,
          cluster_name=cluster_name,
        ),
      )
      return
    else:
      op.add_failed(
        resource=env,
        reason=op.prep_msg(
          op.FAILURE_REASON,
          cluster_name=cluster_name,
        ),
        remediation=op.prep_msg(op.FAILURE_REMEDIATION),
      )
      return


class SnapshotLoadStability(runbook.Step):
  """Check the stability of the Composer environment's Snapshot Load via cloud logging.

  This step queries Cloud Logging to see if the snapshot load had any issues.
  """

  template = 'composer::snapshot_load_stability'

  def execute(self):
    """Check if the Composer environment's snapshot load had any issues."""
    env = op.get('env')
    project_id = op.get('project_id')
    cluster_name = op.get('cluster_name')
    start_time_utc = op.get('start_time')
    end_time_utc = op.get('end_time')
    try:
      failed_to_load_snapshot_log_entries = logs.realtime_query(
        project_id=project_id,
        filter_str="""resource.type="cloud_composer_environment"
          resource.labels.environment_name="{}"
          Search("Failed to load the snapshot due to the following error:")
          OR Search("Message about failure reason is not present in job output.")
          """.format(env.name),
        start_time=start_time_utc,
        end_time=end_time_utc,
      )
    except utils.GcpApiError as e:
      op.add_skipped(
        resource=env,
        reason=f'Failed to query snapshot load stability logs: {e}',
      )
      return
    if failed_to_load_snapshot_log_entries:
      op.info('Checking for OOM in cluster logs.')
      try:
        oom_log_entries = logs.realtime_query(
          project_id=project_id,
          filter_str="""resource.type="k8s_node"
            resource.labels.cluster_name="{}"
            jsonPayload.message:"load-snapshot-"
            log_id("events")
            (jsonPayload.reason:("OOMKilling" OR "SystemOOM")
            OR jsonPayload.message:("OOM encountered" OR "out of memory"))
            """.format(cluster_name),
          start_time=start_time_utc,
          end_time=end_time_utc,
        )
      except utils.GcpApiError as e:
        op.add_skipped(
          resource=env,
          reason=f'Failed to query OOM logs: {e}',
        )
        return
      if oom_log_entries:
        op.add_failed(
          resource=env,
          reason=op.prep_msg(
            op.FAILURE_REASON_ALT1,
            cluster_name=cluster_name,
          ),
          remediation=op.prep_msg(op.FAILURE_REMEDIATION_ALT1),
        )
        return
      else:
        op.add_failed(
          resource=env,
          reason=op.prep_msg(
            op.FAILURE_REASON,
            cluster_name=cluster_name,
          ),
          remediation=op.prep_msg(op.FAILURE_REMEDIATION),
        )
        return
    else:
      op.add_ok(
        resource=env,
        reason=op.prep_msg(
          op.SUCCESS_REASON,
          cluster_name=cluster_name,
        ),
      )


class MonitoringStability(runbook.Step):
  """Check the stability of the Composer environment's Monitoring Pod via cloud logging.

  This step queries Cloud Logging to see if the monitoring pod has any OOM
  events.
  """

  template = 'composer::monitoring_stability'

  def execute(self):
    """Check if the environment's monitoring pod is running and checking for OOM events."""

    env = op.get('env')
    project_id = op.get('project_id')
    cluster_name = op.get('cluster_name')
    uptime_query = f"""
    fetch k8s_container
    | metric 'kubernetes.io/container/uptime'
    | filter (resource.cluster_name == '{cluster_name}'
      && resource.pod_name =~ 'airflow-monitoring-.*')
    | align mean_aligner(5m)
    | every 5m
    """
    try:
      uptime_results = monitoring.query(project_id, uptime_query)
    except utils.GcpApiError as e:
      op.add_skipped(
        resource=env,
        reason=f'Failed to query monitoring uptime: {e}',
      )
      return

    if not uptime_results:
      op.info(f'Monitoring pod is not running in {cluster_name}. Checking logs for OOM events...')

      start_time = op.get('start_time')
      end_time = op.get('end_time')
      log_filter = f"""
      resource.type="k8s_node"
      resource.labels.cluster_name="{cluster_name}"
      log_id("events") (jsonPayload.reason:("OOMKilling" OR "SystemOOM")
      OR jsonPayload.message:("OOM encountered" OR "out of memory"))
      severity=WARNING
      jsonPayload.message:"airflow-monitoring-"
      """
      try:
        restart_events = logs.realtime_query(
          project_id=project_id,
          filter_str=log_filter,
          start_time=start_time,
          end_time=end_time,
        )
      except utils.GcpApiError as e:
        op.add_skipped(
          resource=env,
          reason=f'Failed to query monitoring OOM logs: {e}',
        )
        return

      if restart_events:
        op.add_failed(
          resource=env,
          reason=(
            op.prep_msg(
              op.FAILURE_REASON,
              cluster_name=cluster_name,
            )
          ),
          remediation=op.prep_msg(op.FAILURE_REMEDIATION),
        )
        return
      else:
        op.add_failed(
          resource=env,
          reason=op.prep_msg(op.FAILURE_REASON_ALT1),
          remediation=op.prep_msg(op.FAILURE_REMEDIATION_ALT1),
        )
        return
    else:
      op.add_ok(
        resource=env,
        reason=op.prep_msg(
          op.SUCCESS_REASON,
          cluster_name=cluster_name,
        ),
      )


class UnhealthyComposerEnd(runbook.EndStep):
  """End of the runbook."""

  def execute(self):
    """End step."""
    op.info('End of the runbook.')
