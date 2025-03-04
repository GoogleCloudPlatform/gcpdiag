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
import sys
from typing import List

import googleapiclient

from gcpdiag import caching, config, models, utils
from gcpdiag.queries import apis, apis_utils
from gcpdiag.queries.billing import ProjectBillingInfo, get_billing_info


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

  @property
  def default_compute_service_account(self) -> str:
    return f'{self.number}-compute@developer.gserviceaccount.com'

  @property
  def parent(self) -> str:
    return self._resource_data['parent']


@caching.cached_api_call
def get_project(project_id: str) -> Project:
  '''Attempts to retrieve project details for the supplied project id or number.
    If the project is found/accessible, it returns a Project object with the resource data.
    If the project cannot be retrieved, the application raises one of the exceptions below.

    Args:
        project_id (str): The project id or number of
        the project (e.g., "123456789", "example-project").

    Returns:
        Project: An object representing the project's full details.

    Raises:
        utils.GcpApiError: If there is an issue calling the GCP/HTTP Error API.

    Usage:
        When using project identifier from gcpdiag.models.Context

        project = crm.get_project(context.project_id)

        An unknown project identifier
        try:
          project = crm.get_project("123456789")
        except:
          # Handle exception
        else:
          # use project data
  '''
  try:
    logging.info('retrieving project %s ', project_id)
    crm_api = apis.get_api('cloudresourcemanager', 'v3', project_id)
    request = crm_api.projects().get(name=f'projects/{project_id}')
    response = request.execute(num_retries=config.API_RETRIES)
  except googleapiclient.errors.HttpError as e:
    error = utils.GcpApiError(response=e)
    if 'IAM_PERMISSION_DENIED' == error.reason:
      print(
          f'[ERROR]:Authenticated account doesn\'t have access to project details of {project_id}.'
          f'\nExecute:\ngcloud projects add-iam-policy-binding {project_id} --role=roles/viewer'
          '--member="user|group|serviceAccount:EMAIL_ACCOUNT" ',
          file=sys.stderr)
    else:
      print(f'[ERROR]:can\'t access project {project_id}: {error.message}.',
            file=sys.stderr)
    print(
        f'[DEBUG]: An Http Error occurred whiles accessing projects.get \n\n{e}',
        file=sys.stderr)
    raise error from e
  else:
    return Project(resource_data=response)


@caching.cached_api_call
def get_all_projects_in_parent(project_id: str) -> List[ProjectBillingInfo]:
  """Get all projects in the Parent Folder that current user has
  permission to view"""
  projects: List[ProjectBillingInfo] = []
  if (not project_id) or (not apis.is_enabled(project_id, 'cloudbilling')):
    return projects
  project = get_project(project_id)
  p_filter = 'parent.type:'+project.parent.split('/')[0][:-1]\
    +' parent.id:'+project.parent.split('/')[1] if project.parent else ''

  api = apis.get_api('cloudresourcemanager', 'v3')
  for p in apis_utils.list_all(request=api.projects().search(query=p_filter),
                               next_function=api.projects().search_next,
                               response_keyword='projects'):
    try:
      crm_api = apis.get_api('cloudresourcemanager', 'v3', p['projectId'])
      p_name = 'projects/' + p['projectId'] if 'projects/' not in p[
          'projectId'] else p['projectId']
      request = crm_api.projects().get(name=p_name)
      response = request.execute(num_retries=config.API_RETRIES)
      projects.append(
          ProjectBillingInfo(response['projectId'],
                             get_billing_info(p['projectId'])))
    except (utils.GcpApiError, googleapiclient.errors.HttpError) as error:
      if isinstance(error, googleapiclient.errors.HttpError):
        error = utils.GcpApiError(error)
      if error.reason in [
          'IAM_PERMISSION_DENIED', 'USER_PROJECT_DENIED', 'SERVICE_DISABLED'
      ]:
        # skip projects that user does not have permissions on
        continue
      else:
        print(
            f'[ERROR]: An Http Error occurred whiles accessing projects.get \n\n{error}',
            file=sys.stderr)
      raise error from error
  return projects
