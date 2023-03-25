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
"""Queries related to GCP Cloud Run service."""

import logging
import re
from typing import Dict, Iterable, Mapping

import googleapiclient.errors

from gcpdiag import caching, config, models, utils
from gcpdiag.queries import apis


class Service(models.Resource):
  """Represents Cloud Run service."""
  _resource_data: dict

  def __init__(self, project_id, resource_data):
    super().__init__(project_id=project_id)
    self._resource_data = resource_data

  @property
  def name(self) -> str:
    m = re.search(r'/services/([^/]+)$', self._resource_data['name'])
    if not m:
      raise RuntimeError('can\'t determine name of service %s' %
                         (self._resource_data['name']))
    return m.group(1)

  @property
  def id(self) -> str:
    return self._resource_data['uid']

  @property
  def full_path(self) -> str:
    return self._resource_data['name']

  @property
  def short_path(self) -> str:
    path = self.project_id + '/' + self.id
    return path


def get_all_locations(project_id: str) -> Iterable[str]:
  """Return list of all regions

  Args:
      project_id (str): project id for this request

  Raises:
      utils.GcpApiError: Raises GcpApiError in case of query issues

  Returns:
      Iterable[Region]: Return list of all regions
  """
  try:
    cloudrun_api = apis.get_api('run', 'v1', project_id)
    request = cloudrun_api.projects().locations().list(
        name=f'projects/{project_id}')
    response = request.execute(num_retries=config.API_RETRIES)
    if not response or 'locations' not in response:
      return set()

    return {
        location['name']
        for location in response['locations']
        if 'name' in location
    }
  except googleapiclient.errors.HttpError as err:
    raise utils.GcpApiError(err) from err


@caching.cached_api_call
def get_services(context: models.Context) -> Mapping[str, Service]:
  """Get a list of Cloud Run services matching the given context,
  indexed by service id."""
  services: Dict[str, Service] = {}

  if not apis.is_enabled(context.project_id, 'run'):
    return services

  locations = get_all_locations(context.project_id)

  for location in locations:
    m = re.search(r'/locations/([^/]+)$', location)
    if not m:
      continue
    region = m.group(1)
    cloudrun_api = apis.get_api('run', 'v2', context.project_id)
    logging.info(
        'fetching list of cloud run services in the project %s for the region %s',
        context.project_id, region)
    query = cloudrun_api.projects().locations().services().list(
        parent=f'projects/{context.project_id}/locations/{region}')
    try:
      resp = query.execute(num_retries=config.API_RETRIES)
      if 'services' not in resp:
        continue
      for s in resp['services']:
        # projects/{project}/locations/{location}/services/{serviceId}.
        result = re.match(r'projects/[^/]+/locations/([^/]+)/services/([^/]+)',
                          s['name'])
        if not result:
          logging.error('invalid cloudrun name: %s', s['name'])
          raise RuntimeError(
              'missing data in projects.locations.services.list response')
        location = result.group(1)
        labels = s.get('labels', {})
        name = result.group(2)
        if not context.match_project_resource(
            location=location, labels=labels, resource=name):
          continue

        services[s['uid']] = Service(project_id=context.project_id,
                                     resource_data=s)
    except googleapiclient.errors.HttpError as err:
      raise utils.GcpApiError(err) from err
  return services
