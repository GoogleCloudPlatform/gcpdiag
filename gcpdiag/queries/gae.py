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
"""Queries related to GCP App Engine Standard app."""

import logging
import re
from typing import Dict, Mapping

import googleapiclient.errors

from gcpdiag import caching, config, models, utils
from gcpdiag.queries import apis


class Service(models.Resource):
  """Represents an App Engine Standard app service."""
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
    return self._resource_data['id']

  @property
  def full_path(self) -> str:
    return self._resource_data['name']

  @property
  def short_path(self) -> str:
    path = self.project_id + '/' + self.id
    return path


class Version(models.Resource):
  """Represents an App Engine Standard app version."""
  _resource_data: dict
  service: Service

  def __init__(self, project_id, resource_data):
    super().__init__(project_id=project_id)
    self._resource_data = resource_data

  @property
  def id(self) -> str:
    return self._resource_data['id']

  @property
  def full_path(self) -> str:
    return self._resource_data['name']

  @property
  def short_path(self) -> str:
    path = self.project_id + '/' + self.id
    return path

  @property
  def runtime(self) -> str:
    return self._resource_data['runtime']

  @property
  def env(self) -> str:
    return self._resource_data['env']


@caching.cached_api_call
def get_services(context: models.Context) -> Mapping[str, Service]:
  """Get a list of App Engine Standard services matching the given context,
  indexed by service id."""
  services: Dict[str, Service] = {}
  if not apis.is_enabled(context.project_id, 'appengine'):
    return services
  appengine_api = apis.get_api('appengine', 'v1', context.project_id)
  logging.info('fetching list of app engine services in the project %s',
               context.project_id)
  query = appengine_api.apps().services().list(appsId=context.project_id)
  try:
    resp = query.execute(num_retries=config.API_RETRIES)
    if 'services' not in resp:
      return services
    for s in resp['services']:
      # apps/myapp/services/default
      result = re.match(r'apps/[^/]+/services/([^/]+)', s['name'])
      if not result:
        logging.error('invalid appengine data: %s', s['name'])
        continue

      labels = s.get('labels', {})

      if not context.match_project_resource(resource=result.group(1),
                                            labels=labels):
        continue

      services[s['id']] = Service(project_id=context.project_id,
                                  resource_data=s)
  except googleapiclient.errors.HttpError as err:
    raise utils.GcpApiError(err) from err
  return services


@caching.cached_api_call
def get_versions(context: models.Context) -> Mapping[str, Version]:
  """Get a list of App Engine Standard service versions the given context,
    indexed by a version id."""
  versions: Dict[str, Version] = {}
  if not apis.is_enabled(context.project_id, 'appengine'):
    return versions

  appengine_api = apis.get_api('appengine', 'v1', context.project_id)

  services = get_services(context)

  for service in services.values():
    query = appengine_api.apps().services().versions().list(
        appsId=context.project_id, servicesId=service.id)
    try:
      resp = query.execute(num_retries=config.API_RETRIES)
      if 'versions' not in resp:
        return versions
      for resp_s in resp['versions']:
        # verify that we have some minimal data that we expect
        if 'id' not in resp_s:
          raise RuntimeError('missing data in apps.services.list response')
        v = Version(project_id=context.project_id, resource_data=resp_s)
        v.service = service
        versions[v.id] = v
    except googleapiclient.errors.HttpError as err:
      raise utils.GcpApiError(err) from err

    logging.info('fetching list of app engine services in the project %s',
                 context.project_id)

  return versions
