# Lint as: python3
"""Queries related to GCP Projects."""

import functools

from gcp_doctor import config
from gcp_doctor.queries import apis


@functools.lru_cache(maxsize=None)
def get_project_nr(project_id: str) -> int:
  crm_api = apis.get_api('cloudresourcemanager', 'v1')
  request = crm_api.projects().get(projectId=project_id)
  response = request.execute(num_retries=config.API_RETRIES)
  if response and 'projectNumber' in response:
    return response['projectNumber']
  else:
    raise ValueError(f'unknown project: {project_id}')
