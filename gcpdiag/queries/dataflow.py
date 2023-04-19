"""Queries related to Dataflow."""

from datetime import datetime
from typing import List

from gcpdiag import caching, models
from gcpdiag.lint import get_executor
from gcpdiag.queries import apis, apis_utils

DATAFLOW_REGIONS = [
    'asia-northeast2', 'us-central1', 'northamerica-northeast1', 'us-west3',
    'southamerica-east1', 'us-east1', 'asia-northeast1', 'europe-west1',
    'europe-west2', 'asia-northeast3', 'us-west4', 'asia-east2',
    'europe-central2', 'europe-west6', 'us-west2', 'australia-southeast1',
    'europe-west3', 'asia-south1', 'us-west1', 'us-east4', 'asia-southeast1'
]


class Job(models.Resource):
  """ Represents Dataflow job """
  _resource_data: dict
  project_id: str

  def __init__(self, project_id: str, resource_data: dict):
    super().__init__(project_id)
    self._resource_data = resource_data

  @property
  def full_path(self) -> str:
    return self._resource_data['name']

  @property
  def state(self) -> str:
    return self._resource_data['currentState']

  @property
  def minutes_in_current_state(self) -> int:
    timestamp = datetime.strptime(self._resource_data['currentStateTime'],
                                  '%Y-%m-%dT%H:%M:%S.%fZ')
    delta = datetime.now() - timestamp
    return int(delta.total_seconds() // 60)


def get_region_dataflow_jobs(api, context: models.Context,
                             region: str) -> List[Job]:
  jobs = apis_utils.list_all(
      request=api.projects().locations().jobs().list(
          projectId=context.project_id, location=region),
      next_function=api.projects().locations().jobs().list_next,
      response_keyword='jobs')
  return [Job(context.project_id, job_desc) for job_desc in jobs]


@caching.cached_api_call
def get_all_dataflow_jobs(context: models.Context) -> List[Job]:
  api = apis.get_api('dataflow', 'v1b3', context.project_id)

  if not apis.is_enabled(context.project_id, 'dataflow'):
    return []

  result: List[Job] = []
  executor = get_executor()
  for jobs in executor.map(lambda r: get_region_dataflow_jobs(api, context, r),
                           DATAFLOW_REGIONS):
    result += jobs
  return result
