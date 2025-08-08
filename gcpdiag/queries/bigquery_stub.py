# pylint: disable=unused-argument,invalid-name
"""Stub API calls used in bigquery.py for testing."""

import json
import logging
import re
import uuid
from typing import Any, Optional

import httplib2
from googleapiclient import errors

from gcpdiag.queries import apis_stub

HttpError = errors.HttpError


class GetJobRequest(apis_stub.ApiStub):
  """Mocks jobs.get().execute() by loading a specific job file."""

  def __init__(self, project_id: str, location: str, job_id: str):
    super().__init__()
    self.project_id = project_id
    # Handle potential None location passed from get()
    self.location = location.lower() if location else 'us'
    self.short_job_id = job_id.split('.')[-1].split('_')[
        -1]  # More robust split
    self.json_basename = f'job_get_{self.location}_{self.short_job_id}'
    logging.debug('Stub: GetJobRequest prepared for %s', self.json_basename)

  def execute(self, num_retries=0):
    self._maybe_raise_api_exception()
    file_path = None
    try:
      json_dir = apis_stub.get_json_dir(self.project_id)
      file_path = json_dir / f'{self.json_basename}.json'
      with open(file_path, encoding='utf-8') as json_file:
        return json.load(json_file)
    except FileNotFoundError as e:
      logging.warning(
          'Stub: File not found for GetJobRequest: %s. Raising 404.', file_path)
      raise HttpError(httplib2.Response({'status': 404}), b'Not Found') from e
    except Exception as e:
      logging.error(
          'Stub: Error executing GetJobRequest for %s: %s',
          self.json_basename,
          e,
      )
      raise


# Add a stub for getQueryResults
class GetQueryResultsRequest(apis_stub.ApiStub):
  """Mocks jobs.getQueryResults().execute() by loading a specific results file."""

  def __init__(self, project_id: str, location: str, job_id: str):
    super().__init__()
    self.project_id = project_id
    self.location = location.lower() if location else 'us'  # Default if None
    # Extract the UUID part assuming format gcpdiag_query_{uuid}
    self.short_job_id = job_id.split('_')[-1]
    self.json_basename = f'job_results_{self.location}_{self.short_job_id}'
    logging.debug('Stub: GetQueryResultsRequest prepared for %s',
                  self.json_basename)

  def execute(self, num_retries=0):
    self._maybe_raise_api_exception()
    file_path = None
    try:
      json_dir = apis_stub.get_json_dir(self.project_id)
      file_path = json_dir / f'{self.json_basename}.json'
      with open(file_path, encoding='utf-8') as json_file:
        return json.load(json_file)
    except FileNotFoundError:
      # Return a default empty successful result if file not found
      logging.warning(
          'Stub: File not found for GetQueryResultsRequest: %s. Returning empty'
          ' success.',
          file_path,
      )
      return {
          'kind': 'bigquery#getQueryResultsResponse',
          'jobComplete': True,
          'jobReference': {
              'projectId': self.project_id,
              'jobId': f'gcpdiag_query_{self.short_job_id}',
              'location': self.location,
          },
          'schema': {
              'fields': []
          },
          'rows': [],
          'totalRows': '0',
      }
    except Exception as e:
      logging.error(
          'Stub: Error executing GetQueryResultsRequest for %s: %s',
          self.json_basename,
          e,
      )
      raise


# Modify BigQueryJobsStub
class BigQueryJobsStub(apis_stub.ApiStub):
  """Mocks the object returned by bigquery_api.jobs()."""

  # Store job states for simulation - use a class variable
  _job_states: dict[str, list[dict[str, Any]]] = {}

  def insert(self, projectId: str, body: dict[str, Any]):
    """Mocks jobs.insert().

    Args:
      projectId: The ID of the project.
      body: The request body.

    Returns:
      A stub response and prepares state for get().
    """
    job_ref = body.get('jobReference', {})
    job_id = job_ref.get(
        'jobId', f'gcpdiag_query_{uuid.uuid4()}')  # Use provided or generate
    location = job_ref.get('location', 'us')  # Default location
    # Simulate job progression: RUNNING -> DONE (default for success tests)
    # Store states to be returned by subsequent get() calls, unless already set
    # by a test
    if job_id not in BigQueryJobsStub._job_states:
      BigQueryJobsStub._job_states[job_id] = [
          {
              'status': {
                  'state': 'RUNNING'
              },
              'jobReference': {
                  'projectId': projectId,
                  'jobId': job_id,
                  'location': location,
              },
          },
          {
              'status': {
                  'state': 'DONE'
              },
              'jobReference': {
                  'projectId': projectId,
                  'jobId': job_id,
                  'location': location,
              },
          },
      ]
    # Prepare the insert response
    insert_response = {
        'kind': 'bigquery#job',
        'etag': 'some_etag',
        'id': f'{projectId}:{location}.{job_id}',
        'selfLink': f'/projects/{projectId}/jobs/{job_id}?location={location}',
        'jobReference': {
            'projectId': projectId,
            'jobId': job_id,
            'location': location,
        },
        'status': {
            'state': 'PENDING'
        },  # Initial state reported by insert
        'configuration': body.get('configuration'),
    }
    logging.debug(
        'Stub: jobs.insert called for %s. Prepared states: %s',
        job_id,
        BigQueryJobsStub._job_states.get(job_id),
    )
    # Return an object that mimics the execute() method
    return apis_stub.RestCallStub(projectId, '', default=insert_response)

  def get(self, projectId: str, jobId: str, location: Optional[str] = None):
    """Mocks jobs.get(). Returns states based on stored sequence."""
    logging.debug('Stub: jobs.get called for %s, location %s', jobId, location)
    effective_location = location or 'us'  # Use default if None
    if (jobId in BigQueryJobsStub._job_states and
        BigQueryJobsStub._job_states[jobId]):
      next_state = BigQueryJobsStub._job_states[jobId].pop(
          0)  # Get and remove the next state
      logging.debug(
          'Stub: jobs.get returning state: %s',
          next_state.get('status', {}).get('state'),
      )
      # Ensure jobReference matches what get_query_results expects
      if 'jobReference' not in next_state:
        next_state['jobReference'] = {
            'projectId': projectId,
            'jobId': jobId,
            'location': effective_location,
        }
      elif 'location' not in next_state['jobReference']:
        next_state['jobReference']['location'] = effective_location
      # Add other fields if needed, mimicking the real response structure
      next_state.setdefault('kind', 'bigquery#job')
      next_state.setdefault('id', f'{projectId}:{effective_location}.{jobId}')
      next_state.setdefault('status', {}).setdefault(
          'state', 'UNKNOWN')  # Default state if missing
      return apis_stub.RestCallStub(projectId, '', default=next_state)
    else:
      # If no specific state is prepared or states are exhausted, fallback to
      # file or 404
      logging.warning(
          'Stub: No predefined state for job %s. Falling back to file-based'
          ' GetJobRequest.',
          jobId,
      )
      return GetJobRequest(project_id=projectId,
                           location=effective_location,
                           job_id=jobId)

  def getQueryResults(self,
                      projectId: str,
                      jobId: str,
                      location: Optional[str] = None,
                      **kwargs):
    """Mocks jobs.getQueryResults(). Returns a custom request object."""
    logging.debug('Stub: jobs.getQueryResults called for %s, location %s',
                  jobId, location)
    effective_location = location or 'us'  # Use default if None
    return GetQueryResultsRequest(project_id=projectId,
                                  location=effective_location,
                                  job_id=jobId)

  def query(self, projectId: str, body: dict[str, Any]):
    """Mocks jobs.query(). Returns a RestCallStub for the query result."""
    # Keep existing query logic for INFORMATION_SCHEMA
    query_text = body.get('query', '')
    if not isinstance(query_text, str):
      query_text = ''
    job_id_match = re.search(r"job_id\s*=\s*'([^']+)'", query_text)
    schema_match = re.search(
        r'FROM\s*`[^`]+`\.`([^`]+)`\.INFORMATION_SCHEMA\.JOBS',
        query_text,
        re.IGNORECASE,
    )
    json_basename = 'job_query_info_schema_default'
    if job_id_match and schema_match:
      job_id_in_query = job_id_match.group(1)
      short_job_id = job_id_in_query.split('.')[-1]
      region = schema_match.group(1).lower()
      json_basename = f'job_query_info_schema_{region}_{short_job_id}'
      logging.debug(
          'Stub: jobs.query parsed job=%s, region=%s -> basename=%s',
          short_job_id,
          region,
          json_basename,
      )
    else:
      # This is likely not an INFORMATION_SCHEMA query, handle differently if
      # needed
      # For now, assume it's an INFO_SCHEMA query that failed parsing
      if 'INFORMATION_SCHEMA' in query_text.upper():
        logging.warning(
            'Stub: jobs.query could not parse job/region from INFO_SCHEMA'
            ' query: %s',
            query_text,
        )
      else:
        # This could be a direct query call, not handled by get_query_results
        # flow
        logging.error('Stub: jobs.query received unexpected query type: %s',
                      query_text)
        # Return an error or specific response for direct queries if needed
        raise NotImplementedError(
            "Stub doesn't handle direct jobs.query calls yet.")
    default_empty_result = {
        'kind': 'bigquery#queryResponse',
        'schema': {},
        'rows': [],
        'totalRows': '0',
        'jobComplete': True,
    }
    return apis_stub.RestCallStub(
        project_id=projectId,
        json_basename=json_basename,
        default=default_empty_result,
    )


# Update BigQueryApiStub to use the modified BigQueryJobsStub
class BigQueryApiStub(apis_stub.ApiStub):
  """Mocks the top-level BigQuery API object returned by apis.get_api."""

  def __init__(self):
    super().__init__()
    # Ensure a fresh jobs stub instance for each API stub instance
    self._jobs_stub = BigQueryJobsStub()

  def jobs(self):
    """Returns the stub for the jobs resource."""
    return self._jobs_stub

  def new_batch_http_request(self, callback=None):
    raise NotImplementedError(
        'Batch requests not implemented in BigQueryApiStub yet')
