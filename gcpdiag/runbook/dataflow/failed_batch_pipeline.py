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
"""Module containing Dataflow diagnostic tree and custom steps."""

from datetime import datetime, timedelta, timezone
from typing import Union

from gcpdiag import runbook
from gcpdiag.queries import apis, crm, dataflow, monitoring
from gcpdiag.runbook import op
from gcpdiag.runbook.dataflow import flags
from gcpdiag.runbook.dataflow import generalized_steps as dataflow_gs


class FailedBatchPipeline(runbook.DiagnosticTree):
  """Diagnostic checks for failed Dataflow Batch Pipelines.

  Provides a DiagnosticTree to check for issues related to failed batch
  pipelines.

  - Examples:
    - Pipeline failed to launch
    - Workers failed to start or are crashlooping
  """

  parameters = {
    flags.PROJECT_ID: {
      'type': str,
      'help': 'The Project ID of the resource under investigation',
      'required': True,
    },
    flags.DATAFLOW_JOB_ID: {
      'type': str,
      'help': 'The Job ID returned when the launch command is submitted',
      'required': True,
    },
    flags.JOB_REGION: {
      'type': str,
      'help': 'The region configured for the job',
      'required': True,
    },
  }

  def build_tree(self):
    """Construct the diagnostic tree with appropriate steps."""
    # Instantiate step classes and add them to the tree
    start = FailedBatchPipelineStart()
    self.add_start(start)

    batch = JobIsBatch()
    self.add_step(parent=start, child=batch)

    supported_sdk = dataflow_gs.ValidSdk()
    self.add_step(parent=batch, child=supported_sdk)

    quotas_check = dataflow_gs.DataflowQuotas()
    self.add_step(parent=supported_sdk, child=quotas_check)

    job_graph = dataflow_gs.JobGraphIsConstructed()
    self.add_step(parent=quotas_check, child=job_graph)

    job_logs_visible = dataflow_gs.JobLogsVisible()
    self.add_step(parent=job_graph, child=job_logs_visible)

    batch_failed_job_logs = BatchFailedJobLogs()
    self.add_step(parent=job_logs_visible, child=batch_failed_job_logs)

    # Ending the runbook
    self.add_end(FailedBatchPipelineEnd())


class FailedBatchPipelineStart(runbook.StartStep):
  """Start step.

  Gets the job and confirms it exists.
  Usually this will be logged in Dataflow Monitoring Interface, but may not be
  logged if the job graph is not constructed.
  """

  template = 'generics::failed_batch_pipeline_job_found'

  def execute(self):
    """Start Step for failed batch pipelines runbook."""
    project = crm.get_project(op.get(flags.PROJECT_ID))
    job_id = op.get(flags.DATAFLOW_JOB_ID)
    job_region = op.get(flags.JOB_REGION)

    if project:
      op.info(f'name: {project.name}: id: {project.id}')
    product = self.__module__.split('.')[-2]

    if not apis.is_enabled(op.get(flags.PROJECT_ID), 'dataflow'):
      op.add_skipped(project, reason='Dataflow API is not enabled')
      return

    job = dataflow.get_job(op.get(flags.PROJECT_ID), job_id, job_region)
    if job is not None:  # default=None
      success_reason = op.prep_msg(op.SUCCESS_REASON, job_id=job_id, region=job_region)
      op.add_ok(resource=job, reason=success_reason)
    else:
      op.add_skipped(
        resource=project,
        reason=(
          'Could not find job {} or the {} API is disabled in project {}'.format(
            job_id, product, project.id
          )
        ),
      )


class JobIsBatch(runbook.Step):
  """Has step to check if the job is a batch job."""

  def execute(self):
    """Checks if a Dataflow job is indeed a batch job by field JobType."""

    job = dataflow.get_job(
      op.get(flags.PROJECT_ID),
      op.get(flags.DATAFLOW_JOB_ID),
      op.get(flags.JOB_REGION),
    )
    if job.job_type == 'JOB_TYPE_BATCH':
      op.add_ok(resource=job, reason='Job is of type batch')
    else:
      op.add_failed(
        resource=job,
        reason='Dataflow job is not a batch job.',
        remediation='Please pass a batch job',
      )


class BatchFailedJobLogs(runbook.CompositeStep):
  """Has common step to check job state is not failed.

  Usually the specific error is logged in the Dataflow Monitoring Interface.
  """

  template = 'generics::failed_batch_pipeline_check_common_errors'

  def execute(self):
    """Checks that the Dataflow job's state."""

    job = dataflow.get_job(
      op.get(flags.PROJECT_ID),
      op.get(flags.DATAFLOW_JOB_ID),
      op.get(flags.JOB_REGION),
    )

    if job.state == 'JOB_STATE_FAILED':
      op.add_failed(
        resource=job,
        reason='Job has failed.',
        remediation=op.prep_msg(op.FAILURE_REMEDIATION),
      )
      self.add_child(dataflow_gs.JobLogErrors())

    elif job.state in [
      'JOB_STATE_STOPPED',
      'JOB_STATE_PENDING',
      'JOB_STATE_QUEUED',
    ]:
      op.add_uncertain(
        resource=job,
        reason='Job has not yet started to run',
        remediation=('Wait for the job to start running & job graph is constructed to retry'),
      )
    elif job.state in ['JOB_STATE_CANCELLED', 'JOB_STATE_DONE']:
      op.add_ok(resource=job, reason='Job has been terminated successfully')
    elif job.state == 'JOB_STATE_RUNNING':
      op.add_ok(resource=job, reason='Job is running successfully')
      # no fatal errors, check latency/performance
      self.add_child(dataflow_gs.SlowJobLogs())
      self.add_child(BatchWorkerMetrics())


class BatchWorkerMetrics(runbook.Step):
  """Has step to check job's workers.

  Queries the worker vcpu Promql metrics for a running job.
  """

  template = 'generics::slow_batch_metric'

  def execute(self):
    """Checks worker utilization."""
    job = dataflow.get_job(
      op.get(flags.PROJECT_ID),
      op.get(flags.DATAFLOW_JOB_ID),
      op.get(flags.JOB_REGION),
    )

    num_vcpu_promql_query = f"""
      max by (job_id) (
        dataflow_googleapis_com:job_current_num_vcpus{{job_id="{job.id}"}}
      )
    """

    end_time = datetime.now(timezone.utc)
    start_time = end_time - timedelta(days=3)
    num_vcpu_result = monitoring.queryrange(
      op.get(flags.PROJECT_ID), num_vcpu_promql_query, start_time, end_time
    )
    num_vcpu_matrix_data = num_vcpu_result.get('data', {}).get('result', [])
    if not num_vcpu_matrix_data:
      op.add_skipped(resource=job, reason='No worker data found for this job')
    else:
      vcpu_count_data_points = num_vcpu_matrix_data[0].get('values', [])
      vcpu_count = [float(val[1]) for val in vcpu_count_data_points]
      if not vcpu_count:
        op.add_skipped(resource=job, reason='No vCPU data points found for this job')
      elif vcpu_count[-1] == 0:
        op.add_failed(
          resource=job,
          reason='Job is RUNNING but is not provisioned any workers.',
          remediation='Check on GCE quota,autoscaling and stockout log failures',
        )
      else:
        op.add_ok(resource=job, reason=f'Job is processing with {vcpu_count[-1]} workers.')

        high_cpu = self.high_cpu_utilization(end_time, start_time, job.id)
        high_mem = self.high_mem_utilization(end_time, start_time, job.id)

        if high_cpu is True and high_mem is True:
          op.add_failed(
            resource=job,
            reason=op.prep_msg(op.FAILURE_REASON),
            remediation=op.prep_msg(op.FAILURE_REMEDIATION),
          )
        elif high_cpu is True and high_mem is not True:
          op.add_failed(
            resource=job,
            reason='High CPU utilization but low memory utilization',
            remediation=op.prep_msg(op.FAILURE_REMEDIATION),
          )
        elif high_cpu is not True and high_mem is True:
          op.add_failed(
            resource=job,
            reason='Low CPU utilization but high memory utilization',
            remediation=op.prep_msg(op.FAILURE_REMEDIATION),
          )
        else:
          op.add_ok(resource=job, reason='Job is running within reasonable CPU and Memory limits')

    self.add_child(BatchThroughput())

  def high_cpu_utilization(self, end_time, start_time, job_id) -> Union[bool, None]:
    cpu_util_promql_query = f"""
        avg (
            avg_over_time(
                compute_googleapis_com:instance_cpu_utilization{{
                    monitored_resource="gce_instance",
                    metadata_user_dataflow_job_id="{job_id}"
                }}[5m]
            )
        )
        """
    cpu_util_result = monitoring.queryrange(
      op.get(flags.PROJECT_ID), cpu_util_promql_query, start_time, end_time
    )
    cpu_result_matrix_data = cpu_util_result.get('data', {}).get('result', [])
    if not cpu_result_matrix_data:
      return None
    else:
      cpu_data_points = cpu_result_matrix_data[0].get('values', [])
      cpu = [float(val[1]) for val in cpu_data_points]
      if not cpu:
        return None
      else:
        return cpu[-1] > 85

  def high_mem_utilization(self, end_time, start_time, job_id) -> Union[bool, None]:
    mem_util_promql_query = f"""
      avg(
          avg_over_time({{
              __name__="compute.googleapis.com/guest/memory/bytes_used",
              monitored_resource="gce_instance",
              state="used",
              metadata_user_dataflow_job_id="{job_id}"
          }}[5m])
      )
      /
      avg(
          avg_over_time({{
              __name__="compute.googleapis.com/guest/memory/bytes_used",
              monitored_resource="gce_instance",
              metadata_user_dataflow_job_id="{job_id}"
          }}[5m])
      )
      """

    mem_util_result = monitoring.queryrange(
      op.get(flags.PROJECT_ID), mem_util_promql_query, start_time, end_time
    )
    mem_result_matrix_data = mem_util_result.get('data', {}).get('result', [])
    if not mem_result_matrix_data:
      return None
    else:
      mem_data_points = mem_result_matrix_data[0].get('values', [])
      mem = [float(val[1]) for val in mem_data_points]
      if not mem:
        return None
      else:
        return mem[-1] > 85


class BatchThroughput(runbook.Step):
  """Has step to check job throughput is not stalled.

  Queries the throughput Promql metrics for a running job.
  """

  def execute(self):
    """Checks pipeline throughput."""
    job = dataflow.get_job(
      op.get(flags.PROJECT_ID),
      op.get(flags.DATAFLOW_JOB_ID),
      op.get(flags.JOB_REGION),
    )

    throughput_promql_query = f"""sum by (job_id) (
      rate(dataflow_googleapis_com:job_elements_produced_count{{job_id='{job.id}'}}[1m])
      )"""

    inflight_data_promql_query = f"""sum by (job_id) (
      max_over_time(dataflow_googleapis_com:job_estimated_byte_count{{job_id="{job.id}"}}[15m])
      )"""
    end_time = datetime.now(timezone.utc)
    start_time = end_time - timedelta(days=3)
    throughput_metric = monitoring.queryrange(
      op.get(flags.PROJECT_ID), throughput_promql_query, start_time, end_time
    )
    inflight_byte_data_metric = monitoring.queryrange(
      op.get(flags.PROJECT_ID), inflight_data_promql_query, start_time, end_time
    )

    throughput_data = throughput_metric.get('data', {}).get('result', [])
    inflight_data = inflight_byte_data_metric.get('data', {}).get('result', [])

    if not throughput_data or not throughput_data[0].get('values'):
      op.add_skipped(resource=job, reason='No throughput data found for this job')
    elif not inflight_data or not inflight_data[0].get('values'):
      op.add_skipped(resource=job, reason='No estimate inflight backlog data found for this job')
    else:
      throughput_rates = [float(val[1]) for val in throughput_data[0].get('values', [])]
      inflight_byte_data = [float(val[1]) for val in inflight_data[0].get('values', [])]

      if throughput_rates[-1] == 0.0:
        op.add_failed(
          resource=job,
          reason=f"""Job is RUNNING but throughput has stalled at {throughput_rates[-1]}
            elements/sec and {inflight_byte_data[-1]} inflight data""",
          remediation='Check on resource provision/utilization and parallelism as '
          'the job throughput is minimal',
        )
      else:
        op.add_ok(
          resource=job,
          reason=f"""Pipeline is processing at {throughput_rates[-1]} elements/sec
            and {inflight_byte_data[-1]} inflight data""",
        )
    self.add_child(BatchElapsedTime())


class BatchElapsedTime(runbook.Step):
  """Has step to check job elapsed time.

  Queries the elapsed time Promql metrics for a running job.
  """

  def execute(self):
    """Checks the job's elapsed time is not too long."""
    job = dataflow.get_job(
      op.get(flags.PROJECT_ID),
      op.get(flags.DATAFLOW_JOB_ID),
      op.get(flags.JOB_REGION),
    )

    promql_query = f"""
      max by (job_id) (
        dataflow_googleapis_com:job_elapsed_time{{job_id="{job.id}"}}
      )
    """
    end_time = datetime.now(timezone.utc)
    result = monitoring.queryrange(
      op.get(flags.PROJECT_ID), promql_query, (end_time - timedelta(days=3)), end_time
    )
    matrix_data = result.get('data', {}).get('result', [])
    if not matrix_data:
      op.add_skipped(resource=job, reason='No elapsed-time data found for this job')
    else:
      data_points = matrix_data[0].get('values', [])
      elapsed_times = [float(val[1]) for val in data_points]
      if not elapsed_times:
        op.add_skipped(resource=job, reason='No elapsed-time values found for this job')
      elif elapsed_times[-1] > 43200.0:  # elapsed time > 12 hours
        op.add_failed(
          resource=job,
          reason=f'Job is RUNNING but has been running for {elapsed_times[-1]} seconds. '
          'This suggests the job is underprovisioned especially if throughput is not 0.',
          remediation='Check on resource utilization as the job runtime is high',
        )
      else:
        op.add_ok(
          resource=job,
          reason=f'Pipeline has been running for a reasonable duration: {elapsed_times[-1]} seconds.',
        )


class FailedBatchPipelineEnd(runbook.EndStep):
  """End of the runbook.

  No more checks to perform.
  """

  def execute(self):
    """End step."""
    op.info('No more checks to perform.')
