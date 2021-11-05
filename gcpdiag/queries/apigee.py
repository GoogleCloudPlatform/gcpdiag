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
"""Queries related to Apigee."""

from typing import Dict, List, Mapping

import googleapiclient.errors

from gcpdiag import caching, config, models
from gcpdiag.queries import apis
from gcpdiag.utils import GcpApiError


class EnvironmentGroup(models.Resource):
  """Represents an Apigee Environment Group
    https://cloud.google.com/apigee/docs/reference/apis/apigee/rest/v1/organizations.envgroups#resource:-environmentgroup
    """
  _resource_data: dict

  def __init__(self, project_id, resource_data):
    super().__init__(project_id=project_id)
    self._resource_data = resource_data
    self.org_name = project_id

  @property
  def name(self) -> str:
    return self._resource_data['name']

  @property
  def full_path(self) -> str:
    return f'organizations/{self.org_name}/envgroups/{self.name}'

  @property
  def host_names(self) -> List[str]:
    return self._resource_data['hostnames']


@caching.cached_api_call
def get_org(context: models.Context) -> Mapping[str, str]:
  """Get Apigee organizations matching the GCP Project Id"""
  org: Dict[str, str] = {}
  if not apis.is_enabled(context.project_id, 'apigee'):
    return org
  apigee_api = apis.get_api('apigee', 'v1', context.project_id)
  # Apigee Organization : GCP Project = 1 : 1
  query = apigee_api.organizations().list(parent='organizations')
  try:
    resp = query.execute(num_retries=config.API_RETRIES)
    if 'organizations' not in resp:
      return org
    for resp_o in resp['organizations']:
      if 'organization' not in resp_o or 'projectIds' not in resp_o:
        raise RuntimeError('missing data in organizations.list response')
      if context.project_id == resp_o['projectIds'][0]:
        org[context.project_id] = resp_o['organization']
        return org
  except googleapiclient.errors.HttpError as err:
    raise GcpApiError(err) from err
  return org


@caching.cached_api_call
def get_envgroups(org_name: str) -> Mapping[str, EnvironmentGroup]:
  """Get Environment group list by organization name, caching the result."""
  envgroups: Dict[str, EnvironmentGroup] = {}
  apigee_api = apis.get_api('apigee', 'v1')
  # Environment groups per organization limit: 85, set pageSize to 85
  query = apigee_api.organizations().envgroups().list(
      parent=f'organizations/{org_name}', pageSize=85)
  try:
    resource_data = query.execute(num_retries=config.API_RETRIES)
    if 'environmentGroups' not in resource_data:
      return envgroups
    for envgroup in resource_data['environmentGroups']:
      envgroups[envgroup['name']] = EnvironmentGroup(project_id=org_name,
                                                     resource_data=envgroup)
  except googleapiclient.errors.HttpError as err:
    raise GcpApiError(err) from err
  return envgroups


@caching.cached_api_call
def get_envgroups_attachments(envgroup_name: str) -> List[str]:
  """Get Environment group attachments by environment group name, caching the result."""
  environments: List[str] = []
  apigee_api = apis.get_api('apigee', 'v1')
  # Environment group attachments per organization limit: 100, set pageSize to 100
  query = apigee_api.organizations().envgroups().attachments().list(
      parent=envgroup_name, pageSize=100)
  try:
    resource_data = query.execute(num_retries=config.API_RETRIES)
    if 'environmentGroupAttachments' not in resource_data:
      return environments
    for environmentgroupattachments in resource_data[
        'environmentGroupAttachments']:
      environments.append(environmentgroupattachments['environment'])
  except googleapiclient.errors.HttpError as err:
    raise GcpApiError(err) from err
  return environments
