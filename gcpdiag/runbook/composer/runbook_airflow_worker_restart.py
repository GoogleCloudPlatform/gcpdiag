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
"""Runbook addresses the common root causes of Airflow worker restart.

This runbook checks for the following:
- Worker Resource Exhaustion (OOM)
- Subheading: Check for OOMKilled Events in Logs
- Check for SIGKILL / Zombie Tasks
- Check for Ephemeral Storage Exhaustion
- Check for gcs-syncd Memory Limit Issue
- Check for worker Liveness Probe Logs
- Check for Unschedulable Pods
"""

from datetime import datetime

from gcpdiag import runbook, utils
from gcpdiag.queries import composer, logs
from gcpdiag.runbook import op
from gcpdiag.runbook.gce import flags


class RunbookAirflowWorkerRestart(runbook.DiagnosticTree):
  """Runbook addresses the root causes of Airflow worker instability.

  This runbook checks for the following:
  - Verify Composer environment exists and find the associated GKE cluster
  - Check for OOMKilled Events in Logs
  - Check for SIGKILL / Zombie Tasks
  - Check for Ephemeral Storage Exhaustion
  - Check for gcs-syncd Ephemeral Storage Limit Issue
  - Check for Worker Liveness Probe Logs.
  - Check for Unschedulable Pods
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
      'help': 'The start time of the investigation',
      'required': True,
    },
    flags.END_TIME: {
      'type': datetime,
      'help': 'The end time of the investigation',
      'required': True,
    },
  }

  def build_tree(self):
    """Constructs the diagnostic tree with granular steps."""
    start = WorkerRestartStart()
    self.add_start(start)

    oom_check = CheckWorkerOOM()
    zombie_check = CheckZombieTasks()
    storage_check = CheckEphemeralStorage()
    gcs_limit_check = CheckGcsSyncdEphemeralStorageLimit()

    infra = InfrastructureChecks()
    self.add_step(parent=start, child=infra)
    self.add_step(parent=start, child=oom_check)
    self.add_step(parent=start, child=zombie_check)
    self.add_step(parent=start, child=storage_check)
    self.add_step(parent=start, child=gcs_limit_check)
    self.add_end(RunbookAirflowWorkerRestartEnd())


class WorkerRestartStart(runbook.StartStep):
  """Validates environment existence and extracts GKE metadata.

  Gets the environment and cluster name from the user and validates the
  existence of the environment.
  """

  def execute(self):
    """Verify Composer environment exists and find the associated GKE cluster."""
    project_id = op.get(flags.PROJECT_ID)
    env_name = op.get(flags.NAME)

    op.info(f'Validating Composer environment: "{env_name}" in project: "{project_id}"')
    try:
      all_envs = composer.get_environments(op.get_context())
    except utils.GcpApiError as e:
      op.add_skipped(None, reason=f'Failed to get Composer environments:{e}')
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
    op.add_ok(
      resource=selected_env,
      reason=(
        f'Found environment : {env_name} and cluster : {cluster_name} for project {project_id}'
      ),
    )


class _LogCheckStep(runbook.Step):
  """Base class for performing a log query and reporting results."""

  def run_query(self, filter_str):
    """Executes a log query and updates step status using template-defined messages."""
    project_id = op.get(flags.PROJECT_ID)
    selected_env = op.get('selected_env')

    try:
      res = logs.realtime_query(
        project_id=project_id,
        filter_str=filter_str,
        start_time=op.get(flags.START_TIME),
        end_time=op.get(flags.END_TIME),
      )
    except utils.GcpApiError as e:
      op.add_skipped(
        resource=selected_env,
        reason=f'Failed to query logs: {e}',
      )
      return

    if any(res):
      op.add_failed(
        resource=selected_env,
        reason=op.prep_msg(op.FAILURE_REASON),
        remediation=op.prep_msg(op.FAILURE_REMEDIATION),
      )
    else:
      op.add_ok(resource=selected_env, reason=op.prep_msg(op.SUCCESS_REASON))


class CheckWorkerOOM(_LogCheckStep):
  """Check for Out-of-Memory (OOM) events in worker pods.

  This check verifies if there are any OOMKilled events in the worker pods.
  """

  template = 'airflow::check_worker_oom'

  def execute(self):
    """Check for Out-of-Memory (OOM) events in worker pods."""
    cluster = op.get('cluster_name')
    lql_filter = f"""
    resource.labels.cluster_name="{cluster}"
    (
      (SEARCH("out of memory") AND ("airflow task su" OR "airflow task ru"))
      OR jsonPayload.reason:("OOMKilling" OR "SystemOOM")
      OR SEARCH("OOMKilled")
    )
    """
    self.run_query(lql_filter)


class CheckZombieTasks(_LogCheckStep):
  """Check for Zombie tasks or SIGKILL signals in environment logs.

  This check verifies if there are any Zombie tasks or SIGKILL signals in the
  environment logs.
  """

  template = 'airflow::check_zombie_tasks'

  def execute(self):
    """Check for Zombie tasks or SIGKILL signals in environment logs."""
    env_name = op.get(flags.NAME)
    lql_filter = f"""
    resource.type="cloud_composer_environment"
    resource.labels.environment_name="{env_name}"
    (textPayload:"Negsignal.SIGKILL"
    OR textPayload:"Task exited with return code -9"
    OR textPayload:"Detected zombie job")
    """
    self.run_query(lql_filter)


class CheckEphemeralStorage(_LogCheckStep):
  """Check for worker pod evictions due to ephemeral storage exhaustion.

  This check verifies if there are any worker pod evictions due to ephemeral
  storage exhaustion.
  """

  template = 'airflow::check_ephemeral_storage'

  def execute(self):
    """Check for worker pod evictions due to ephemeral storage exhaustion."""
    cluster = op.get('cluster_name')
    lql_filter = f"""
    resource.labels.cluster_name="{cluster}"
    SEARCH("Pod ephemeral local storage usage exceeds the total limit")
    AND SEARCH("A worker pod was evicted")
    """
    self.run_query(lql_filter)


class CheckGcsSyncdEphemeralStorageLimit(_LogCheckStep):
  """Check for gcs-syncd container hitting its ephemeral limit.

  This check verifies if there are any gcs-syncd container is hitting its
  ephemeral
  limit.
  """

  template = 'airflow::check_gcs_syncd_limit'

  def execute(self):
    """Check for gcs-syncd container hitting its ephemeral limit."""
    cluster = op.get('cluster_name')
    lql_filter = f"""
    resource.type="k8s_container"
    resource.labels.cluster_name="{cluster}"
    SEARCH("Container gcs-syncd exceeded its local ephemeral storage limit")
    """
    self.run_query(lql_filter)


class InfrastructureChecks(runbook.CompositeStep):
  """Composite step for GKE and Pod stability investigations.

  This composite step checks for the following:
  - Liveness Probe failures on worker pods
  - Scheduling issues due to quota issues
  - Worker pod restarts due to GKE preemption
  """

  def execute(self):
    """Checking for:

    - Liveness Probe failures on worker pods
    - Scheduling issues due to quota issues
    - Worker pod restarts due to GKE preemption
    """
    self.add_child(CheckLivenessProbes())
    self.add_child(CheckSchedulingFailures())
    self.add_child(CheckGkePreemption())


class CheckLivenessProbes(_LogCheckStep):
  """Checks for failed Liveness probes on worker pods.

  This check verifies if there are any Liveness probes failed on worker pods.
  """

  template = 'airflow::check_liveness_probes'

  def execute(self):
    """Checks for failed Liveness probes on worker pods."""
    cluster = op.get('cluster_name')
    lql_filter = f"""
    resource.labels.cluster_name="{cluster}"
    jsonPayload.involvedObject.kind="Pod"
    jsonPayload.involvedObject.name=~"^airflow-worker.*"
    SEARCH("Liveness probe failed")
    """
    self.run_query(lql_filter)


class CheckSchedulingFailures(_LogCheckStep):
  """Check for worker pods failing to schedule due to quota issues.

  This check verifies if there are any worker pods failing to schedule due to
  quota issues.
  """

  template = 'airflow::check_scheduling_failures'

  def execute(self):
    """Check for worker pods failing to schedule due to quota issues."""
    project_id = op.get(flags.PROJECT_ID)
    cluster = op.get('cluster_name')
    lql_filter = f"""
    resource.type="gce_cluster_autoscaler"
    resource.labels.project_id="{project_id}"
    resource.labels.cluster_name="{cluster}"
    (jsonPayload.resultError.errorId="cloud_quota_exceeded"
    OR jsonPayload.noScaleUp.unhandledSignals.reasons.message:"max node group size reached")
    """
    self.run_query(lql_filter)


class CheckGkePreemption(_LogCheckStep):
  """Check if worker pods were preempted by GKE.

  This check verifies if there are any worker pods were preempted by GKE.
  """

  template = 'airflow::check_gke_preemption'

  def execute(self):
    """Check if worker pods were preempted by GKE."""
    cluster = op.get('cluster_name')
    lql_filter = f"""
    resource.type="k8s_pod"
    resource.labels.cluster_name="{cluster}"
    jsonPayload.reason="Preempted"
    jsonPayload.involvedObject.name=~"^airflow-worker.*"
    """
    self.run_query(lql_filter)


class RunbookAirflowWorkerRestartEnd(runbook.EndStep):
  """End step for Airflow worker restart runbook."""

  def execute(self):
    """End step for Airflow worker restart runbook."""
    op.info('End of the runbook')
