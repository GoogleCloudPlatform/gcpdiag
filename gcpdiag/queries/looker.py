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

# Lint as: python3
"""Queries related to GCP Looker Core."""
import logging
from typing import Dict

import googleapiclient.errors

from gcpdiag import caching, models, utils
from gcpdiag.queries import apis, apis_utils
from gcpdiag.utils import Version


class Instance(models.Resource):
  """Represents a Looker Core Instance.

  https://cloud.google.com/looker/docs/reference/rest/v1/projects.locations.instances#Instance
  """

  _resource_data: Dict
  master_version: Version

  def __init__(self, project_id, resource_data):
    super().__init__(project_id=project_id)
    self._resource_data = resource_data

  @property
  def name(self) -> str:
    return self._resource_data['name']

  @property
  def create_time(self) -> str:
    return self._resource_data['createTime']

  @property
  def update_time(self) -> str:
    return self._resource_data['updateTime']

  @property
  def status(self) -> str:
    return self._resource_data['state']

  @property
  def platform_edition(self) -> str:
    return self._resource_data['platformEdition']

  @property
  def looker_version(self) -> str:
    return self._resource_data['lookerVersion']

  @property
  def egress_public_ip(self) -> str:
    return self._resource_data['egressPublicIp']

  @property
  def ingress_public_ip(self) -> str:
    return self._resource_data['ingressPublicIp']

  @property
  def looker_uri(self) -> str:
    return self._resource_data['lookerUri']

  @property
  def public_ip_enabled(self) -> str:
    return self._resource_data['publicIpEnabled']

  @property
  def full_path(self) -> str:
    return self._resource_data['name']


@caching.cached_api_call
def get_instances(context: models.Context) -> Dict[str, Instance]:
  """Get a list of Instances from the given GCP project"""
  instances: Dict[str, Instance] = {}
  if not apis.is_enabled(context.project_id, 'looker'):
    return instances
  looker_api = apis.get_api('looker', 'v1', context.project_id)
  l_filter = 'projects/' + context.project_id
  try:
    logging.info('fetching list of all locations in given project %s',
                 context.project_id)
    for l in apis_utils.list_all(
        request=looker_api.projects().locations().list(name=l_filter),
        next_function=looker_api.projects().locations().list_next,
        response_keyword='locations'):
      logging.info('fetching list of all locations in given location %s',
                   l['locationId'])
      i_filter = 'projects/' + context.project_id + '/locations/' + l[
          'locationId']
      for i in apis_utils.list_all(
          request=looker_api.projects().locations().instances().list(
              parent=i_filter),
          next_function=looker_api.projects().locations().instances().list_next,
          response_keyword='instances'):

        if not context.match_project_resource(resource=i.get('name', '')):
          continue
        i = Instance(project_id=context.project_id, resource_data=i)
        instances[i.name] = i
  except googleapiclient.errors.HttpError as err:
    logging.error('failed to list instances: %s', err)
    raise utils.GcpApiError(err) from err
  return instances


@caching.cached_api_call
def get_only_instances(context: models.Context) -> Dict[str, Instance]:
  """Get a list of Instances from the given GCP project"""
  instances: Dict[str, Instance] = {}
  if not apis.is_enabled(context.project_id, 'looker'):
    return instances
  looker_api = apis.get_api('looker', 'v1', context.project_id)

  logging.info('fetching list of all locations in given project %s',
               context.project_id)
  try:
    i_filter = 'projects/' + context.project_id + '/locations/us-central1'
    for i in apis_utils.list_all(
        request=looker_api.projects().locations().instances().list(
            parent=i_filter),
        next_function=looker_api.projects().locations().instances().list_next,
        response_keyword='instances'):

      if not context.match_project_resource(resource=i.get('name', '')):
        continue
      i = Instance(project_id=context.project_id, resource_data=i)
      instances[i.name] = i
  except googleapiclient.errors.HttpError as err:
    logging.error('failed to list instances: %s', err)
    raise utils.GcpApiError(err) from err
  return instances
