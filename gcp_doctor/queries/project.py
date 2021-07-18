# Copyright 2021 Google LLC
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

# Lint as: python3
"""Queries related to GCP Projects."""

import logging
import re
from typing import Dict, Mapping

import googleapiclient.errors

from gcp_doctor import caching, config
from gcp_doctor.queries import apis
from gcp_doctor.utils import GcpApiError

diskcache = caching.get_cache()


class Project():
  """Represents a Project resource.

  See also the API documentation:
  https://cloud.google.com/compute/docs/reference/rest/v1/projects/get
  """
  _id: str
  _metadata: Dict[str, str]
  _resource_data: dict

  def __init__(self, project_id, resource_data):
    self._id = project_id
    self._resource_data = resource_data

  @property
  def number(self) -> int:
    return get_project_nr(self._id)

  @property
  def id(self) -> str:
    """Project id (not project number)."""
    return self._id

  @property
  def name(self) -> str:
    return self._resource_data['name']

  @property
  def full_path(self) -> str:
    result = re.match(r'https://www.googleapis.com/compute/v1/(.*)',
                      self._resource_data['selfLink'])
    if result:
      return result.group(1)
    else:
      return '>> ' + self._resource_data['selfLink']

  @property
  def short_path(self) -> str:
    path = self._id + '/' + self.name
    return path

  @property
  def gce_metadata(self) -> Mapping[str, str]:
    mapped_metadata: Dict[str, str] = {}

    metadata = self._resource_data.get('commonInstanceMetadata')
    if metadata and 'items' in metadata:
      for m_item in metadata['items']:
        mapped_metadata[m_item.get('key')] = m_item.get('value')
    return mapped_metadata


@caching.cached_api_call(expire=config.STATIC_DOCUMENTS_EXPIRY_SECONDS)
def get_project_nr(project_id: str) -> int:
  logging.info('retrieving project nr. of project %s', project_id)
  crm_api = apis.get_api('cloudresourcemanager', 'v1')
  request = crm_api.projects().get(projectId=project_id)
  response = request.execute(num_retries=config.API_RETRIES)
  if response and 'projectNumber' in response:
    return response['projectNumber']
  else:
    raise ValueError(f'unknown project: {project_id}')


@caching.cached_api_call(in_memory=True)
def get_project(project_id: str) -> Project:
  gce_api = apis.get_api('compute', 'v1')
  query = gce_api.projects().get(project=project_id)
  logging.info('fetching data for project %s', project_id)
  try:
    response = query.execute(num_retries=config.API_RETRIES)
  except googleapiclient.errors.HttpError as err:
    raise GcpApiError(err) from err
  return Project(project_id=project_id, resource_data=response)
