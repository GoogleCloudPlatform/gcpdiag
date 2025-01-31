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
"""Module containing Dataflow diagnostic tree and custom steps."""

from gcpdiag import runbook
from gcpdiag.queries import apis, crm, dataflow, logs
from gcpdiag.runbook import op
from gcpdiag.runbook.dataflow import flags
from gcpdiag.runbook.dataflow import generalized_steps as dataflow_gs

# from gcpdiag.runbook.iam import generalized_steps as iam_gs


class FailedStreamingPipeline(runbook.DiagnosticTree):
  """Diagnostic checks for failed Dataflow Streaming Pipelines.

  Provides a DiagnosticTree to check for issues related to failed streaming
  pipelines.

  - Examples:
    - Pipeline failed to launch
    - Workers not starting
  """

  parameters = {
      flags.PROJECT_ID: {
          'type': str,
          'help': 'The Project ID of the resource under investigation',
          'required': True,
      },
      flags.JOB_ID: {
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
    # Instantiate your step classes
    start = FailedStreamingPipelineStart()
    # add them to your tree
    self.add_start(start)

    streaming = JobIsStreaming()
    self.add_step(parent=start, child=streaming)

    supported_sdk = dataflow_gs.ValidSdk()
    self.add_step(parent=streaming, child=supported_sdk)

    job_graph = JobGraphIsConstructed()
    self.add_step(parent=supported_sdk, child=job_graph)

    # Ending your runbook
    self.add_end(FailedStreamingPipelineEnd())


class FailedStreamingPipelineStart(runbook.StartStep):
  """Start step.

  Gets the job and confirms it exists.
  Usually this will be logged in Dataflow Monitoring Interface, but may not be
  logged if the job
  graph is not constructed.
  """

  template = 'generics::failed_streaming_pipeline_job_found'

  def execute(self):
    """Start Step for failed streaming pipelines runbook."""
    project = crm.get_project(op.get(flags.PROJECT_ID))
    job_id = op.get(flags.JOB_ID)
    job_region = op.get(flags.JOB_REGION)

    if project:
      op.info(f'name: {project.name}: id: {project.id}')
    product = self.__module__.split('.')[-2]

    if not apis.is_enabled(op.get(flags.PROJECT_ID), 'dataflow'):
      op.add_skipped(project, reason='Dataflow API is not enabled')

    job = dataflow.get_job(op.get(flags.PROJECT_ID), job_id, job_region)
    if job is not None:  # default=None
      success_reason = op.prep_msg(op.SUCCESS_REASON,
                                   job_id=job_id,
                                   region=job_region)
      op.add_ok(resource=job, reason=success_reason)
    else:
      op.add_skipped(
          resource=project,
          reason=(
              'Could not find job {} or the {} API is disabled in project {}'.
              format(job_id, product, project.id)),
      )


class JobIsStreaming(runbook.Step):
  """Has common step to check if the job is a streaming job."""

  def execute(self):
    """Checks if a Dataflow job is indeed a streaming job by field JobType."""

    job = dataflow.get_job(op.get(flags.PROJECT_ID), op.get(flags.JOB_ID),
                           op.get(flags.JOB_REGION))
    if job.job_type == 'JOB_TYPE_STREAMING':
      op.add_ok(resource=job, reason='Job is of type streaming')
    else:
      op.add_failed(
          resource=job,
          reason='Dataflow job is not a streaming job.',
          remediation='Please pass a streaming job',
      )


class JobState(runbook.Step):
  """Has common step to check job state is not failed.

  Usually the specific error is logged in the Dataflow Monitoring Interface.
  """

  template = 'generics::failed_streaming_pipeline_check_common_errors'

  def execute(self):
    """Checks that the Dataflow job's state."""
    job = dataflow.get_job(op.get(flags.PROJECT_ID), op.get(flags.JOB_ID),
                           op.get(flags.JOB_REGION))

    if job.state == 'JOB_STATE_FAILED':
      log_filter = ['severity=WARNING']
      project_id = op.get(flags.PROJECT_ID)
      log_name = 'log_id("dataflow.googleapis.com/worker")'
      project_logs = {}

      project_logs[project_id] = logs.query(
          project_id=project_id,
          resource_type='dataflow_step',
          log_name=log_name,
          filter_str=' AND '.join(log_filter),
      )

      for log_entry in project_logs[project_id].entries:
        if log_entry['severity'] >= 'ERROR':
          op.info(
              message=
              f'Error logs found in job logs for the project {job.full_path}')

      failure_reason = op.prep_msg(op.FAILURE_REASON,
                                   job_id=op.get(flags.JOB_ID))
      failure_remediation = op.prep_msg(op.FAILURE_REMEDIATION)

      op.add_failed(
          resource=job,
          reason=failure_reason,
          remediation=failure_remediation,
      )
    elif job.state in [
        'JOB_STATE_STOPPED',
        'JOB_STATE_PENDING',
        'JOB_STATE_QUEUED',
    ]:
      op.add_uncertain(
          resource=job,
          reason='Job has not yet started to run',
          remediation=(
              'Wait for the job to start running & job graph is constructed to'
              ' retry'),
      )
    elif job.state in ['JOB_STATE_CANCELLED', 'JOB_STATE_DRAINED']:
      op.add_ok(resource=job, reason='Job has been terminated successfully')
    elif job.state == 'JOB_STATE_RUNNING':
      op.add_ok(resource=job, reason='Job is running successfully')


class JobGraphIsConstructed(runbook.Gateway):
  """Has common step to check if the job has an error in graph construction.

  If a job fails during graph construction, it's error is not logged in the
  Dataflow Monitoring Interface as it never launched. The error appears in the
  console or terminal window where job is ran and may be language-specific.
  Manual check if there's any error using the 3 supported languages: Java,
  Python, Go.
  """

  def execute(self):
    """Checks if a Dataflow job graph is successfully constructed."""
    job = dataflow.get_job(op.get(flags.PROJECT_ID), op.get(flags.JOB_ID),
                           op.get(flags.JOB_REGION))
    message = (
        'Does the job experience any graph or pipeline construction errors'
        ' e.g.wording like %s')

    example_wording = ''
    if 'java' in job.sdk_language.lower():
      example_wording = (
          'Exception in thread "main" java.lang.IllegalStateException')
    elif 'python' in job.sdk_language.lower():
      example_wording = (
          'TypeCheckError: Input type hint violation at group: expected Tuple ,'
          ' got str')
    elif 'go' in job.sdk_language.lower():
      example_wording = (
          'panic: Method ProcessElement in DoFn main.extractFn is missing all'
          ' inputs')

    response = op.prompt(message=message % example_wording,
                         kind=op.CONFIRMATION)

    if response == op.YES:
      op.add_failed(
          resource=job,
          reason='Job was not launched',
          remediation='Correct job launch errors and retry.',
      )
      self.add_child(child=FailedStreamingPipelineEnd())
    else:
      self.add_child(child=JobLogsVisible())


class JobLogsVisible(runbook.Step):
  """Has step to check if the project has logs exclusion filter for dataflow logs.

  This affects visibility of the error causing job failure. If there are no logs
  on the
  Dataflow Monitoring Interface or the launching console/platform, this is a
  good check
  to make sure Dataflow logs are visible.
  """

  def execute(self):
    """Checks if a Dataflow job has visible logs."""

    if not dataflow.logs_excluded(op.get(flags.PROJECT_ID)):
      op.add_ok(
          resource=crm.get_project(op.get(flags.PROJECT_ID)),
          reason='Dataflow Logs are not excluded',
      )
    elif dataflow.logs_excluded(op.get(flags.PROJECT_ID)) is None:
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
              ' failures, or route them to a visible sink'),
      )


class FailedStreamingPipelineEnd(runbook.EndStep):
  """End of the runbook.

  No more checks to perform.
  """

  def execute(self):
    """End step."""
    op.info('No more checks to perform.')
