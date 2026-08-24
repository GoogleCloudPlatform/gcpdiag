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

"""Runbook for troubleshooting Airflow Redis."""

from datetime import datetime

from gcpdiag import runbook, utils
from gcpdiag.queries import composer, logs
from gcpdiag.runbook import op
from gcpdiag.runbook.gce import flags


class RedisTroubleshooting(runbook.DiagnosticTree):
  """Runbook for troubleshooting Redis.

  - Redis OOM (Memory Exhaustion)
  - Failure to authenticate due to Invalid Password
  - Firewall rules blocking Redis traffic
  - Check Celery broker publishing timeouts
  """

  parameters = {
    flags.PROJECT_ID: {
      'type': str,
      'help': 'The Project ID of the resource under investigation',
      'required': True,
    },
    flags.NAME: {
      'type': str,
      'help': 'The name of the Cloud Composer environment',
      'required': True,
    },
    flags.START_TIME: {
      'type': datetime,
      'help': 'The start time of the time range to query logs.',
    },
    flags.END_TIME: {
      'type': datetime,
      'help': 'The end time of the time range to query logs.',
    },
  }

  def build_tree(self):
    """Construct the diagnostic tree with appropriate steps."""
    start = RedisTroubleshootingStart()
    redis_oom = CheckRedisOOM()
    redis_oom_node = CheckRedisOOMNode()
    redis_auth = CheckAuth()
    redis_firewall = CheckFirewall()
    redis_celery = CheckCeleryBrokerPublishingTimeouts()
    end = RedisEnd()

    self.add_start(step=start)
    self.add_step(parent=start, child=redis_oom)
    self.add_step(parent=start, child=redis_oom_node)
    self.add_step(parent=start, child=redis_auth)
    self.add_step(parent=start, child=redis_firewall)
    self.add_step(parent=start, child=redis_celery)
    self.add_end(step=end)


class RedisTroubleshootingStart(runbook.StartStep):
  """Validates environment existence and extracts GKE metadata."""

  def execute(self):
    """Validate environment existence and extract GKE metadata."""
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
        f'Found environment : {env_name} and GKE cluster : {cluster_name} for project {project_id}'
      ),
    )


class LogCheckStep(runbook.Step):
  """Base class for performing a log query and reporting results."""

  def run_query(self, filter_str: str) -> None:
    """Executes a log query and updates step status using template-defined messages.

    Args:
      filter_str: The Cloud Logging filter string to use for the query.
    """
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

    if res:
      op.add_failed(
        resource=selected_env,
        reason=op.prep_msg(op.FAILURE_REASON),
        remediation=op.prep_msg(op.FAILURE_REMEDIATION),
      )
    else:
      op.add_ok(resource=selected_env, reason=op.prep_msg(op.SUCCESS_REASON))


class CheckRedisOOM(LogCheckStep):
  """Check for Redis OOM on Container."""

  template = 'redis::redis_oom'

  def execute(self) -> None:
    """Check for Redis OOM on Container."""
    cluster_name = op.get('cluster_name')
    if not cluster_name:
      op.add_skipped(None, reason='GKE cluster name is missing.')
      return

    container_query = f"""
    resource.labels.cluster_name="{cluster_name}"
    resource.type="k8s_container"
    labels."k8s-pod/run"="airflow-redis"
    SEARCH("OOMKilled")
    """
    self.run_query(container_query)


class CheckRedisOOMNode(LogCheckStep):
  """Check for Redis OOM on Node."""

  template = 'redis::redis_oom_node'

  def execute(self) -> None:
    """Check for Redis OOM on Node."""
    cluster_name = op.get('cluster_name')
    if not cluster_name:
      op.add_skipped(None, reason='GKE cluster name is missing.')
      return

    node_query = f"""
    resource.labels.cluster_name="{cluster_name}"
    resource.type="k8s_node"
    log_id("events")
    jsonPayload.message:"Killed process"
    jsonPayload.message:"airflow-redis"
    """
    self.run_query(node_query)


class CheckAuth(LogCheckStep):
  """Check for Redis authentication failures."""

  template = 'redis::redis_auth'

  def execute(self) -> None:
    """Check for Redis authentication failures."""
    selected_env = op.get('selected_env')
    if not selected_env:
      op.add_skipped(None, reason='Composer environment is missing.')
      return
    op.info(f'Selected environment: {selected_env.name}')
    auth_query = f"""
    resource.type="cloud_composer_environment"
    resource.labels.environment_name="{selected_env.name}"
    textPayload=~"redis.exceptions.AuthenticationError"
    """
    self.run_query(auth_query)


class CheckFirewall(LogCheckStep):
  """Check for Firewall rules blocking Redis traffic."""

  template = 'redis::redis_firewall'

  def execute(self) -> None:
    """Check for Firewall rules blocking Redis traffic."""

    selected_env = op.get('selected_env')
    if not selected_env:
      op.add_skipped(None, reason='Composer environment is missing.')
      return
    firewall_query = """
    resource.type="gce_subnetwork"
    log_id("compute.googleapis.com/firewall")
    jsonPayload.disposition="DENIED"
    jsonPayload.connection.dest_port="6379"
    """
    self.run_query(firewall_query)


class CheckCeleryBrokerPublishingTimeouts(LogCheckStep):
  """Check for Celery broker publishing timeouts."""

  template = 'redis::redis_celery_broker_publishing_timeouts'

  def execute(self) -> None:
    """Check for Celery broker publishing timeouts."""
    selected_env = op.get('selected_env')
    if not selected_env:
      op.add_skipped(None, reason='Composer environment is missing.')
      return
    celery_broker_publishing_timeouts_query = f"""
    resource.type="cloud_composer_environment"
    resource.labels.environment_name="{selected_env.name}"
    log_id("airflow-scheduler")
    textPayload=~"Error sending Celery task"
    """
    self.run_query(celery_broker_publishing_timeouts_query)


class RedisEnd(runbook.EndStep):
  """End step for Redis troubleshooting."""

  def execute(self):
    """End step for Redis troubleshooting."""
    op.info('Redis troubleshooting complete.')
