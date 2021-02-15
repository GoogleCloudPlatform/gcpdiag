# Lint as: python3
"""Queries related to GCP Projects."""

import logging

from gcp_doctor import cache, config
from gcp_doctor.queries import apis

diskcache = cache.get_cache()


# Project IDs and numbers can't be changed, so use the disk cache.
@diskcache.memoize()
def get_project_nr(project_id: str) -> int:
  logging.info('retrieving project nr. of project %s', project_id)
  crm_api = apis.get_api('cloudresourcemanager', 'v1')
  request = crm_api.projects().get(projectId=project_id)
  response = request.execute(num_retries=config.API_RETRIES)
  if response and 'projectNumber' in response:
    return response['projectNumber']
  else:
    raise ValueError(f'unknown project: {project_id}')
