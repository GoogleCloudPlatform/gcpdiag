# Copyright 2025 Google LLC
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
"""Module containing the BigQuery Failed Query diagnostic tree and its steps.

This runbook investigates why a specific BigQuery job failed by verifying the
job status and analyzing the error message against a set of known issues to
provide root cause and remediation steps.
"""

from google.auth import exceptions
from googleapiclient import errors

from gcpdiag import runbook, utils
from gcpdiag.queries import apis, bigquery, crm
from gcpdiag.runbook import op
from gcpdiag.runbook.bigquery import constants, flags
from gcpdiag.runbook.bigquery import generalized_steps as bigquery_gs


class FailedQuery(runbook.DiagnosticTree):
  """Diagnoses issues with a failed BigQuery query job.

  This runbook investigates why a specific BigQuery job failed by verifying the
  job's status and analyzing the error message against a set of known issues to
  provide targeted remediation steps.
  """

  parameters = {
      flags.PROJECT_ID: {
          'type': str,
          'help': 'The Project ID where the BigQuery job was run.',
          'required': True,
      },
      flags.BQ_JOB_REGION: {
          'type': str,
          'help': 'The region where the BigQuery job was run.',
          'required': True,
      },
      flags.BQ_JOB_ID: {
          'type': str,
          'help': 'The identifier of the failed BigQuery Job.',
          'required': True,
      },
      flags.BQ_SKIP_PERMISSION_CHECK: {
          'type':
              bool,
          'help':
              'Indicates whether to skip the permission check to speed up the investigation.',
          'required':
              False,
          'default':
              False,
      },
  }

  def build_tree(self):
    """Constructs the diagnostic tree with a logical sequence of steps."""
    start = BigQueryFailedQueryStart()
    self.add_start(start)
    permissions_check = bigquery_gs.RunPermissionChecks('Failed Query Runbook')
    self.add_step(parent=start, child=permissions_check)
    job_exists = BigQueryJobExists()
    self.add_step(parent=permissions_check, child=job_exists)
    self.add_end(BigQueryEnd())


class BigQueryFailedQueryStart(runbook.StartStep):
  """Validates parameters and prerequisites before starting the diagnosis.

  This initial step ensures that the provided project exists, valid job
  identifiers have been provided, the BigQuery API is enabled and also
  checks whether the user has the necessary permissions to execute the
  runbook. The runbook will terminate if any of these initial checks fail.
  """

  def execute(self):
    """Verifying input parameters and the BigQuery API status."""
    project_id = op.get(flags.PROJECT_ID)
    job_region = op.get(flags.BQ_JOB_REGION).lower()
    job_id = op.get(flags.BQ_JOB_ID)
    project_placeholder = crm.Project(resource_data={
        'name': 'projects/0000000000000',
        'projectId': project_id
    })
    user_email = ''
    try:
      user_email = apis.get_user_email()
    except (RuntimeError, exceptions.DefaultCredentialsError):
      op.add_info(
          'Unable to fetch user email. Please make sure to authenticate properly before '
          'executing the investigation. Attempting to run the investigation.')
    except AttributeError as err:
      if (('has no attribute' in str(err)) and
          ('with_quota_project' in str(err))):
        op.info('Running the investigation within the GCA context.')
    if project_id:
      if job_region.lower() in bigquery.BIGQUERY_REGIONS:
        if job_id:
          op.info('Provided job input parameters have the correct format')
        else:
          op.add_skipped(
              resource=project_placeholder,
              reason=
              'Invalid job identifier provided - a job identifier cannot be an empty string.'
          )
          return
      else:
        op.add_skipped(
            resource=project_placeholder,
            reason=
            'Invalid job region provided. Please provide a valid BigQuery region.'
        )
        return
    else:
      op.add_skipped(
          resource=project_placeholder,
          reason=
          'Invalid project identifier provided - the project identifier cannot be an empty string.'
      )
      return
    project = project_placeholder
    try:
      project = bigquery.get_bigquery_project(project_id)
      if not project:
        op.add_skipped(
            project_placeholder,
            reason=
            f'Project "{project_id}" not found or you lack access permissions',
        )
        return
    except utils.GcpApiError as err:
      if 'not found or deleted' in err.message.lower():
        op.add_skipped(
            project_placeholder,
            reason=
            f'Project "{project_id}" not found or deleted. Provide a valid project identifier',
        )
        return
      elif 'caller does not have required permission to use project' in err.message.lower(
      ):
        op.add_skipped(
            project_placeholder,
            reason=(
                f'You do not have permissions to access project "{project_id}". \
              \nEnsure {user_email} has the "serviceusage.services.use" and '
                '"serviceusage.services.list" permissions'),
        )
        return
      elif ('resourcemanager.projects.get' in err.message.lower() and
            'denied on resource' in err.message.lower()):
        op.info(
            f'User {user_email} does not have access to perform a resourcemanager.projects.get'
            ' operation to fetch project metadata, or the project might not exist. Runbook '
            'execution success will depend on project existence and the user having the '
            'minimal required permissions.')
    try:
      is_bq_api_enabled = apis.is_enabled(project_id, 'bigquery')
      if not is_bq_api_enabled:
        op.add_skipped(
            project,
            reason=
            f'BigQuery API is not enabled in project {project_id}. Terminating investigation.',
        )
        return
      else:
        op.info('The BigQuery API is enabled.')
    except utils.GcpApiError as err:
      if 'access' in err.message.lower(
      ) or 'permission denied' in err.message.lower():
        op.info(
            f'User {user_email} does not have access to check the API status.\nRunbook execution '
            'success will depend on the BigQuery API being enabled.')


class BigQueryJobExists(runbook.Gateway):
  """Gateway that verifies the BigQuery Job exists.

  This step calls the BigQuery API to fetch the job. If the job is found, the
  runbook proceeds to the next step. If it is not found (e.g., due to a typo in
  the job ID or region), the runbook reports this and terminates this path.
  """

  template = 'generics::job_exists'

  def execute(self):
    """Verifies that the BigQuery Job exists and directs the flow."""
    project_id = op.get(flags.PROJECT_ID)
    project = crm.Project(resource_data={
        'name': 'projects/0000000000000',
        'projectId': project_id
    })
    try:
      project = bigquery.get_bigquery_project(project_id)
    except (utils.GcpApiError, errors.HttpError):
      pass
    job = None
    try:
      job = bigquery.get_bigquery_job(project_id, op.get(flags.BQ_JOB_REGION),
                                      op.get(flags.BQ_JOB_ID),
                                      op.get(flags.BQ_SKIP_PERMISSION_CHECK))
    except utils.GcpApiError as err:
      if 'not found' in err.message.lower():
        op.add_failed(
            project,
            reason=op.prep_msg(op.FAILURE_REASON,
                               job_id=(op.get(flags.PROJECT_ID) + ':' +
                                       op.get(flags.BQ_JOB_REGION) + '.' +
                                       op.get(flags.BQ_JOB_ID))),
            remediation=op.prep_msg(op.FAILURE_REMEDIATION),
        )
        self.add_child(BigQueryEnd())
        return
      elif 'access denied' in err.message.lower():
        user_email = ''
        try:
          user_email = apis.get_user_email()
        except (RuntimeError, exceptions.DefaultCredentialsError):
          op.warning(
              message=
              'Unable to fetch user email. Please make sure to authenticate properly'
              ' before executing the investigation.')
        except AttributeError as error:
          if (('has no attribute' in str(error)) and
              ('with_quota_project' in str(error))):
            op.info('Running the investigation within the GCA context.')
        warning = 'Insufficient permissions to access BigQuery job metadata.\nGrant at least the'
        warning += (' following permissions to ' + user_email + ':\n')
        warning += 'bigquery.jobs.get, bigquery.jobs.create, serviceusage.services.use and '
        warning += 'serviceusage.services.list .\nTerminating the investigation.'
        op.add_skipped(
            project,
            reason=warning,
        )
        self.add_child(BigQueryEnd())
        return
    if job:
      op.add_ok(job, reason=op.prep_msg(op.SUCCESS_REASON, job_id=job.id))
      self.add_child(ConfirmBQJobIsDone())
    else:
      op.add_failed(
          project,
          reason=op.prep_msg(op.FAILURE_REASON,
                             job_id=(op.get(flags.PROJECT_ID) + ':' +
                                     op.get(flags.BQ_JOB_REGION) + '.' +
                                     op.get(flags.BQ_JOB_ID))),
          remediation=op.prep_msg(op.FAILURE_REMEDIATION),
      )
      self.add_child(BigQueryEnd())


class ConfirmBQJobIsDone(runbook.Gateway):
  """Gateway to confirm that the BigQuery job has finished execution.

  This step checks the job's status. If the status is 'DONE', the runbook
  continues to the next check. If the job is still 'RUNNING' or 'PENDING', the
  runbook will stop and advise the user to wait for completion.
  """

  template = 'generics::job_is_done'

  def execute(self):
    """Confirming job is in a 'DONE' state..."""
    job = bigquery.get_bigquery_job(op.get(flags.PROJECT_ID),
                                    op.get(flags.BQ_JOB_REGION),
                                    op.get(flags.BQ_JOB_ID),
                                    op.get(flags.BQ_SKIP_PERMISSION_CHECK))
    if not job:
      op.add_skipped(op.get(flags.PROJECT_ID),
                     reason='Cannot retrieve job details.')
      return
    if job.job_state == 'DONE':
      op.add_ok(job, reason=op.prep_msg(op.SUCCESS_REASON, job_id=job.id))
      self.add_child(CheckBQJobHasFailed())
    else:
      op.add_failed(
          job,
          reason=op.prep_msg(op.FAILURE_REASON,
                             job_id=job.id,
                             job_state=job.job_state),
          remediation=op.prep_msg(op.FAILURE_REMEDIATION),
      )
      self.add_child(BigQueryEnd())


class CheckBQJobHasFailed(runbook.Gateway):
  """Gateway to verify that a completed job contains an error result.

  This step inspects the job details to see if an error was reported. If an
  error is present, the runbook proceeds to the final analysis step. If the job
  completed successfully, the runbook stops and informs the user.
  """

  template = 'generics::job_has_failed'

  def execute(self):
    """Verifies if a completed job contains an error result."""
    job = bigquery.get_bigquery_job(op.get(flags.PROJECT_ID),
                                    op.get(flags.BQ_JOB_REGION),
                                    op.get(flags.BQ_JOB_ID),
                                    op.get(flags.BQ_SKIP_PERMISSION_CHECK))
    if not job:
      op.add_skipped(op.get(flags.PROJECT_ID),
                     reason='Cannot retrieve job details.')
      return
    if job.job_error_result:
      op.add_ok(
          job,
          reason=op.prep_msg(
              op.SUCCESS_REASON,
              job_id=job.id,
          ),
      )
      self.add_child(BigQueryErrorIdentification())
    else:
      skip_reason = op.prep_msg(op.FAILURE_REASON,
                                job_id=job.id) + '\n' + op.prep_msg(
                                    op.FAILURE_REMEDIATION)
      op.add_skipped(job, reason=skip_reason)
      self.add_child(BigQueryEnd())


class BigQueryErrorIdentification(runbook.Step):
  """Analyzes the job's error message to find a known mitigation.

  This is the final diagnostic step. It collects all error messages from the job
  and compares them against a dictionary of known issues (the ERROR_MAP). If a
  match is found, it provides a specific cause and remediation. Otherwise, it
  reports the full error for manual inspection.
  """

  template = 'generics::error_identification'

  def execute(self):
    """Analyzing error message for known root causes and remediation steps."""
    job = bigquery.get_bigquery_job(op.get(flags.PROJECT_ID),
                                    op.get(flags.BQ_JOB_REGION),
                                    op.get(flags.BQ_JOB_ID),
                                    op.get(flags.BQ_SKIP_PERMISSION_CHECK))
    if not job or not job.job_error_result:
      op.add_skipped(op.get(flags.PROJECT_ID),
                     reason='Cannot retrieve job error details for analysis.')
      return
    unique_errors = set()
    if job.job_error_result and job.job_error_result.get('message'):
      unique_errors.add(job.job_error_result['message'])
    for err in job.job_errors:
      if err.get('message'):
        if err.get('message') not in unique_errors:
          unique_errors.add(err['message'])
        else:
          continue
    if not unique_errors:
      op.add_uncertain(
          job,
          reason='The job failed but returned no error message to analyze.')
      return

    has_matched = False
    for error_text in unique_errors:
      error_message_searchable = error_text.lower()
      for error_substrings, details in constants.ERROR_MAP.items():
        error_substrings_lower = [
            error_substring.lower() for error_substring in error_substrings
        ]
        if all(error_substring_lower in error_message_searchable
               for error_substring_lower in error_substrings_lower):
          has_matched = True
          op.add_failed(
              job,
              reason=op.prep_msg(
                  op.FAILURE_REASON,
                  error_message=error_text,
                  cause=details['cause'],
              ),
              remediation=op.prep_msg(op.FAILURE_REMEDIATION,
                                      remediation=details['remediation']),
          )
          break
    if not has_matched:
      uncertain_error_text = '\n'.join(sorted(list(unique_errors)))
      op.add_uncertain(
          job,
          reason=op.prep_msg(
              op.UNCERTAIN_REASON,
              job_id=job.id,
              error_message=uncertain_error_text,
          ),
          remediation=op.prep_msg(op.UNCERTAIN_REMEDIATION),
      )


class BigQueryEnd(runbook.EndStep):
  """End of the runbook.

  No more checks to perform.
  """

  def execute(self):
    """End step."""
    op.info('No more checks to perform.')
