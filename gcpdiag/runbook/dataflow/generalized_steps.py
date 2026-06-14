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
"""Common steps for Dataflow runbooks."""

import re
from typing import Tuple

from gcpdiag import runbook
from gcpdiag.queries import crm, dataflow, logs, monitoring, quotas
from gcpdiag.runbook import op
from gcpdiag.runbook.dataflow import constants, flags


class ValidSdk(runbook.Step):
  """Has common step to check if the job is running a valid SDK.

  Contains SDK check Step that are likely to be reused for most Dataflow
  Runbooks.
  """

  def execute(self):
    """Checks SDK is not in the list that might trigger known SDK issues."""
    job = dataflow.get_job(
      op.get(flags.PROJECT_ID),
      op.get(flags.DATAFLOW_JOB_ID),
      op.get(flags.JOB_REGION),
    )
    if job is None:
      op.add_skipped(resource=None, reason='Job not found.')
      return

    if job.sdk_support_status != 'SUPPORTED':
      op.add_failed(
        resource=None,
        reason=('Dataflow job Beam SDK is not supported. The pipeline may be rejected.'),
        remediation='Please use a supported Beam SDK version',
      )
    else:
      op.add_ok(resource=job, reason='Dataflow job Beam SDK is supported.')


class JobGraphIsConstructed(runbook.Step):
  """Has common step to check if the job has an error in graph construction.

  If a job fails during graph construction, it's error is not logged in the
  Dataflow Monitoring Interface as it never launched. The error appears in the
  console or terminal window where job is ran and may be language-specific.
  Manual check if there's any error using the 3 supported languages: Java,
  Python, Go.
  """

  def execute(self):
    """Checks if a Dataflow job graph is successfully constructed."""
    job = dataflow.get_job(
      op.get(flags.PROJECT_ID),
      op.get(flags.DATAFLOW_JOB_ID),
      op.get(flags.JOB_REGION),
    )
    message = (
      'Does the job experience any graph or pipeline construction errors e.g.wording like %s'
    )

    example_wording = ''
    if 'java' in job.sdk_language.lower():
      example_wording = 'Exception in thread "main" java.lang.IllegalStateException'
    elif 'python' in job.sdk_language.lower():
      example_wording = (
        'TypeCheckError: Input type hint violation at group: expected Tuple , got str'
      )
    elif 'go' in job.sdk_language.lower():
      example_wording = 'panic: Method ProcessElement in DoFn main.extractFn is missing all inputs'

    response = op.prompt(message=message % example_wording, kind=op.CONFIRMATION)

    if response == op.YES:
      op.add_failed(
        resource=job,
        reason='Job was not launched',
        remediation='Correct job launch errors and retry.',
      )
    else:
      op.add_ok(resource=job, reason='Job graph successfully created')


class JobLogsVisible(runbook.Step):
  """Has step to check if the project has logs exclusion filter for dataflow logs.

  This affects visibility of the error causing job failure. If there are no logs
  on the Dataflow Monitoring Interface or the launching console/platform, this is a
  good check to make sure Dataflow logs are visible.
  """

  def execute(self):
    """Checks if a Dataflow job has visible logs."""
    excluded = dataflow.logs_excluded(op.get(flags.PROJECT_ID))

    if excluded is False:
      op.add_ok(
        resource=crm.get_project(op.get(flags.PROJECT_ID)),
        reason='Dataflow Logs are not excluded',
      )
    elif excluded is None:
      op.add_failed(
        resource=None,
        reason='logging API is disabled',
        remediation='Enable Logging API',
      )
    else:
      op.add_failed(
        resource=crm.get_project(op.get(flags.PROJECT_ID)),
        reason='Dataflow Logs are excluded',
        remediation=(
          'Please include Dataflow logs to allow troubleshooting job'
          ' failures, or route them to a visible sink'
        ),
      )


class DataflowQuotas(runbook.Step):
  """Has common step to check if any Dataflow quotas are being exceeded in the project.

  This step checks if any quotas have been exceeded.
  """

  template = 'generics::quota_exceeded'

  def execute(self):
    """Checks if any Dataflow quotas are being exceeded."""
    if self.quota_exceeded_found() is True:
      op.add_failed(
        resource=crm.get_project(op.get(flags.PROJECT_ID)),
        reason=op.prep_msg(op.FAILURE_REASON),
        remediation=op.prep_msg(op.FAILURE_REMEDIATION),
      )
    else:
      op.add_ok(
        resource=crm.get_project(op.get(flags.PROJECT_ID)),
        reason='Quota usage is within project limits.',
      )

  def quota_exceeded_found(self) -> bool:
    """Catches all signals related to exceeded quotas"""
    quota_exceeded_query_dataflow = quotas.QUOTA_EXCEEDED_HOURLY_PER_SERVICE_QUERY_TEMPLATE.format(
      service_name='dataflow', within_days=1
    )

    quota_exceeded_query_gce = quotas.QUOTA_EXCEEDED_HOURLY_PER_SERVICE_QUERY_TEMPLATE.format(
      service_name='compute', within_days=1
    )
    # pipeline project quotas
    time_series_dataflow = monitoring.query(op.get(flags.PROJECT_ID), quota_exceeded_query_dataflow)
    # worker project quotas
    time_series_gce = monitoring.query(op.get(flags.PROJECT_ID), quota_exceeded_query_gce)

    # possible fatal & non-fatal quota exceeded logs
    quota_error_logs = self.quota_exceeded_logs()

    if time_series_dataflow or time_series_gce or quota_error_logs:
      return True
    return False

  def quota_exceeded_logs(self) -> bool:
    """Catches all logs specifically related to exceeded quotas"""
    job = dataflow.get_job(
      op.get(flags.PROJECT_ID),
      op.get(flags.DATAFLOW_JOB_ID),
      op.get(flags.JOB_REGION),
    )

    log_filter = ['severity>=WARNING', f'resource.labels.job_id={job.id}']
    log_name = f'projects/{op.get(flags.PROJECT_ID)}/logs/dataflow.googleapis.com%2Fworker'
    project_id = op.get(flags.PROJECT_ID)
    job_logs = {}

    job_logs[project_id] = logs.query(
      project_id=project_id,
      resource_type='dataflow_step',
      log_name=log_name,
      filter_str=' AND '.join(log_filter),
    )

    for log_entry in job_logs[project_id].entries:
      log_error = log_entry.get('textPayload', '')
      if constants.TOO_HIGH_VOLUME_LOGGING in log_error:
        # not necessarily a job failed error but some logs will
        # not be allowed from exceeded logging rate
        op.info(
          message='Logging rate is exceeding quota, '
          'considering reducing the rate of logging as per '
          'https://docs.cloud.google.com/dataflow/docs/guides/logging#LogLimits'
        )
      # add fatal quota errors below
    return False


class JobLogErrors(runbook.Step):
  """Has common step to check the job has fatal errors .

  This step checks if any fatal errors appear in either batch/streaming jobs.
  """

  template = 'generics::failed_batch_pipeline_check_common_errors'

  def execute(self):
    job = dataflow.get_job(
      op.get(flags.PROJECT_ID),
      op.get(flags.DATAFLOW_JOB_ID),
      op.get(flags.JOB_REGION),
    )

    log_filter = ['severity>=ERROR', f'resource.labels.job_id={job.id}']
    project_id = op.get(flags.PROJECT_ID)
    job_logs = {}
    log_name = 'log_id("") OR logName:*'

    message_err = constants.GENERIC_ERR
    job_logs[project_id] = logs.query(
      project_id=project_id,
      resource_type='dataflow_step',
      log_name=log_name,
      filter_str=' AND '.join(log_filter),
    )

    for log_entry in job_logs[project_id].entries:
      log_error = log_entry.get('textPayload', '')
      if log_entry['severity'] >= 'ERROR':
        message_err = self.fatal_errors(log_error)
        op.info(message=message_err)

        failure_reason = op.prep_msg(op.FAILURE_REASON, job_id=op.get(flags.DATAFLOW_JOB_ID))
        failure_remediation = op.prep_msg(op.FAILURE_REMEDIATION)

        op.add_failed(
          resource=job,
          reason=failure_reason,
          remediation=failure_remediation,
        )
      elif constants.BATCH_WORKER_STARTUP_CONFIRMATION in log_error:
        op.info('Workers successfully started.')

  def fatal_errors(self, log_error: str) -> str:
    """Specifies actionable fatal job errors."""
    message_err = constants.GENERIC_ERR
    # avoid transient errors that don't cause job failure/stuckness
    if constants.BATCH_JOB_FAILED_ERR in log_error:
      return f'{message_err}; {log_error}'
    elif (
      constants.BATCH_WORKER_STARTUP_FAILURE1 in log_error
      or constants.BATCH_WORKER_STARTUP_FAILURE2 in log_error
      or constants.BATCH_WORKER_STARTUP_FAILURE3 in log_error
    ):
      return f"""{message_err}; {log_error}; check worker startup errors
      (https://docs.cloud.google.com/dataflow/docs/guides/common-errors#error-syncing-pod)"""
    elif (
      constants.BATCH_OUT_OF_MEMORY_FAILURE1 in log_error
      or constants.BATCH_OUT_OF_MEMORY_FAILURE2 in log_error
      or constants.BATCH_OUT_OF_MEMORY_FAILURE3 in log_error
    ):
      return f"""{message_err}; {log_error}; check for out of memory errors
              (https://docs.cloud.google.com/dataflow/docs/guides/troubleshoot-oom)"""
    elif (
      constants.BAD_MACHINE_TYPE_FAILURE1 in log_error
      or constants.BAD_MACHINE_TYPE_FAILURE2 in log_error
    ):
      return f'{message_err}; {log_error}; check for errors in the submitted machine type'
    elif constants.STOCKOUT_ERR1 in log_error or constants.STOCKOUT_ERR2 in log_error:
      return f"""{message_err}; {log_error};
      check for stockout issues and retry with a different machine type or region
      (https://docs.cloud.google.com/architecture/disaster-recovery#dataflow)"""

    # Add batch job errors here
    # Add streaming job errors here
    return message_err


class SlowJobLogs(runbook.Step):
  """Has common step to check the job has processing/throughput errors.

  This step checks if any processing errors appear in either batch/streaming jobs.
  """

  template = 'generics::slow_batch_logs'

  def execute(self):
    """Used to check for any logs that indicate a slow job."""
    job = dataflow.get_job(
      op.get(flags.PROJECT_ID),
      op.get(flags.DATAFLOW_JOB_ID),
      op.get(flags.JOB_REGION),
    )

    log_filter = ['severity>=WARNING', f'resource.labels.job_id={job.id}']
    project_id = op.get(flags.PROJECT_ID)
    job_logs = {}
    log_name = 'log_id("") OR logName:*'

    job_logs[project_id] = logs.query(
      project_id=project_id,
      resource_type='dataflow_step',
      log_name=log_name,
      filter_str=' AND '.join(log_filter),
    )

    for log_entry in job_logs[project_id].entries:
      log_error = log_entry.get('textPayload', '')

      message_err = self.errors(log_error)
      op.info(message=message_err)

      if message_err != constants.GENERIC_WARNING:
        failure_reason = op.prep_msg(op.FAILURE_REASON, job_error=message_err[0])
        failure_remediation = op.prep_msg(op.FAILURE_REMEDIATION, remediation_hint=message_err[1])

        op.add_failed(
          resource=job,
          reason=failure_reason,
          remediation=failure_remediation,
        )

  def errors(self, log_error: str) -> Tuple[str, str]:
    """Specifies actionable job error/warnings.

    For each error, return a tuple pair of : error, remediation. Simplify both & wrap
    in a set to capture a single instance of the error hinted in case of multiple
    violations of the same kind. Finally show the top 10 to avoid flooding output.
    """
    message_err = constants.GENERIC_WARNING
    hot_key_pattern = re.compile(r'A hot key\s+(?P<hot_key>.+?)\s+was detected in', re.IGNORECASE)

    stuck_pattern = re.compile(
      r'Operation ongoing in step|'
      r'Processing stuck in step|'
      r'Operation ongoing for over|'
      r'Operation ongoing in transform|'
      r'Operation ongoing in bundle'
    )

    if hot_key_pattern.search(log_error):
      return (
        'Hot key detected in the job; confirm with asymmetric worker CPU usage metrics.',
        'Consider redistributing keys using a redistribute transform',
      )
    elif stuck_pattern.search(log_error):
      return (
        'Slow executing DoFn detected',
        'Check system latency and wall time metrics for slow DoFns, straggler steps, and/or'
        ' investigating (ssh) the worker. Consider enabling Cloud Profiler for tracing.',
      )

    # Add batch job errors here
    # Add streaming job errors here
    return message_err
