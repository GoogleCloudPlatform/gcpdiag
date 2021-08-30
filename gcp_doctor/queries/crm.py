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
"""Queries related to Resource Manager (projects, resources)."""

import logging
import re

from gcp_doctor import caching, config, models
from gcp_doctor.queries import apis


class Project(models.Resource):
  """Represents a Project resource.

  See also the API documentation:
  https://cloud.google.com/resource-manager/reference/rest/v3/projects/get
  """
  _id: str
  _resource_data: dict
  _number: int

  def __init__(self, resource_data):
    super().__init__(project_id=resource_data['projectId'])
    self._id = resource_data['projectId']
    self._resource_data = resource_data
    match = re.match(r'projects/(\d+)$', resource_data['name'])
    if not match:
      raise ValueError(f'can\'t determine project id ({resource_data})')
    self._number = int(match.group(1))

  @property
  def number(self) -> int:
    return self._number

  @property
  def id(self) -> str:
    """Project id (not project number)."""
    return self._id

  @property
  def name(self) -> str:
    return self._resource_data['displayName']

  @property
  def full_path(self) -> str:
    return f'projects/{self._id}'

  @property
  def short_path(self) -> str:
    return self._id


@caching.cached_api_call
def get_project(project_id: str) -> Project:
  logging.info('retrieving project nr. of project %s', project_id)
  crm_api = apis.get_api('cloudresourcemanager', 'v3', project_id)
  request = crm_api.projects().get(name=f'projects/{project_id}')
  response = request.execute(num_retries=config.API_RETRIES)
  if response:
    return Project(resource_data=response)
  else:
    raise ValueError(f'unknown project: {project_id}')
