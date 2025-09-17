"""Queries related to Dataflow."""

import logging
from datetime import datetime
from typing import List, Optional, Union

import googleapiclient.errors

from gcpdiag import caching, config, models, utils
from gcpdiag.executor import get_executor
from gcpdiag.queries import apis, apis_utils, logs

DATAFLOW_REGIONS = [
    'asia-northeast2', 'us-central1', 'northamerica-northeast1', 'us-west3',
    'southamerica-east1', 'us-east1', 'asia-northeast1', 'europe-west1',
    'europe-west2', 'asia-northeast3', 'us-west4', 'asia-east2',
    'europe-central2', 'europe-west6', 'us-west2', 'australia-southeast1',
    'europe-west3', 'asia-south1', 'us-west1', 'us-east4', 'asia-southeast1'
]


class Job(models.Resource):
  """Represents Dataflow job.

  resource_data is of the form similar to:
  {'id': 'my_job_id',
  'projectId': 'my_project_id',
  'name': 'pubsubtogcs-20240328-122953',
  'environment': {},
  'currentState': 'JOB_STATE_FAILED',
  'currentStateTime': '2024-03-28T12:34:27.383249Z',
  'createTime': '2024-03-28T12:29:55.284524Z',
  'location': 'europe-west2',
  'startTime': '2024-03-28T12:29:55.284524Z'}
  """
  _resource_data: dict
  project_id: str

  def __init__(self, project_id: str, resource_data: dict):
    super().__init__(project_id)
    self._resource_data = resource_data

  @property
  def full_path(self) -> str:
    return self._resource_data['name']

  @property
  def id(self) -> str:
    return self._resource_data['id']

  @property
  def state(self) -> str:
    return self._resource_data['currentState']

  @property
  def job_type(self) -> str:
    return self._resource_data['type']

  @property
  def location(self) -> str:
    return self._resource_data['location']

  @property
  def sdk_support_status(self) -> str:
    return self._resource_data['jobMetadata']['sdkVersion']['sdkSupportStatus']

  @property
  def sdk_language(self) -> str:
    return self._resource_data['jobMetadata']['sdkVersion'][
        'versionDisplayName']

  @property
  def minutes_in_current_state(self) -> int:
    timestamp = datetime.strptime(self._resource_data['currentStateTime'],
                                  '%Y-%m-%dT%H:%M:%S.%fZ')
    delta = datetime.now() - timestamp
    return int(delta.total_seconds() // 60)


def get_region_dataflow_jobs(api, context: models.Context,
                             region: str) -> List[Job]:
  response = apis_utils.list_all(
      request=api.projects().locations().jobs().list(
          projectId=context.project_id, location=region),
      next_function=api.projects().locations().jobs().list_next,
      response_keyword='jobs')
  jobs = []
  for job in response:
    location = job.get('location', '')
    labels = job.get('labels', {})
    name = job.get('name', '')

    # add job id as one of labels for filtering
    labels['id'] = job.get('id', '')

    # we could get the specific job but correctly matching the location will take too
    # much effort. Hence get all the jobs and filter afterwards
    # https://cloud.google.com/dataflow/docs/reference/rest/v1b3/projects.jobs/list#query-parameters
    if not context.match_project_resource(
        location=location, labels=labels, resource=name):
      continue
    jobs.append(Job(context.project_id, job))
  return jobs


@caching.cached_api_call
def get_all_dataflow_jobs(context: models.Context) -> List[Job]:
  api = apis.get_api('dataflow', 'v1b3', context.project_id)

  if not apis.is_enabled(context.project_id, 'dataflow'):
    return []

  result: List[Job] = []
  executor = get_executor(context)
  for jobs in executor.map(lambda r: get_region_dataflow_jobs(api, context, r),
                           DATAFLOW_REGIONS):
    result += jobs

  print(f'\n\nFound {len(result)} Dataflow jobs\n')

  # print one Dataflow job id when it is found
  if context.labels and result and 'id' in context.labels:
    print(f'{result[0].full_path} - {result[0].id}\n')

  return result


@caching.cached_api_call
def get_job(project_id: str, job: str, region: str) -> Union[Job, None]:
  """Fetch a specific Dataflow job."""
  api = apis.get_api('dataflow', 'v1b3', project_id)

  if not apis.is_enabled(project_id, 'dataflow'):
    return None

  query = (api.projects().locations().jobs().get(projectId=project_id,
                                                 location=region,
                                                 jobId=job))
  try:
    resp = query.execute(num_retries=config.API_RETRIES)
    return Job(project_id, resp)
  except googleapiclient.errors.HttpError as err:
    raise utils.GcpApiError(err) from err


@caching.cached_api_call
def get_all_dataflow_jobs_for_project(
    project_id: str,
    filter_str: Optional[str] = None,
) -> Union[List[Job], None]:
  """Fetch all Dataflow jobs for a project."""
  api = apis.get_api('dataflow', 'v1b3', project_id)

  if not apis.is_enabled(project_id, 'dataflow'):
    return None

  jobs: List[Job] = []

  request = (api.projects().jobs().aggregated(projectId=project_id,
                                              filter=filter_str))
  logging.debug('listing dataflow jobs of project %s', project_id)

  while request:  # Continue as long as there are pages
    response = request.execute(num_retries=config.API_RETRIES)
    if 'jobs' in response:
      jobs.extend([Job(project_id, job) for job in response['jobs']])
    request = (api.projects().jobs().aggregated_next(
        previous_request=request, previous_response=response))
  return jobs


@caching.cached_api_call
def logs_excluded(project_id: str) -> Union[bool, None]:
  """Check if Dataflow Logs are excluded."""

  if not apis.is_enabled(project_id, 'dataflow'):
    return None

  exclusions = logs.exclusions(project_id)
  if exclusions is None:
    return None
  else:
    for log_exclusion in exclusions:
      if 'resource.type="dataflow_step"' in log_exclusion.filter and log_exclusion.disabled:
        return True
  return False
