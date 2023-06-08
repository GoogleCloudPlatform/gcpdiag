# Copyright 2023 Google LLC
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
"""Queries related to GCP Vertex AI Workbench Notebooks
"""

import enum
import logging
import re
from typing import Dict, Mapping

import googleapiclient.errors

from gcpdiag import caching, config, models, utils
from gcpdiag.queries import apis

HEALTH_STATE_KEY = 'healthState'
HEALTH_INFO_KEY = 'healthInfo'
INSTANCES_KEY = 'instances'
RUNTIMES_KEY = 'runtimes'
NAME_KEY = 'name'


class HealthStateEnum(enum.Enum):
  """Vertex AI Workbench user-managed notebooks instance health states

  https://cloud.google.com/vertex-ai/docs/workbench/reference/rest/v1/projects.locations.instances/getInstanceHealth#healthstate
  """

  HEALTH_STATE_UNSPECIFIED = 'HEALTH_STATE_UNSPECIFIED'
  HEALTHY = 'HEALTHY'
  UNHEALTHY = 'UNHEALTHY'
  AGENT_NOT_INSTALLED = 'AGENT_NOT_INSTALLED'
  AGENT_NOT_RUNNING = 'AGENT_NOT_RUNNING'

  def __str__(self):
    return str(self.value)


class Instance(models.Resource):
  """Represent a Vertex AI Workbench user-managed notebook instance

  https://cloud.google.com/vertex-ai/docs/workbench/reference/rest/v1/projects.locations.instances#resource:-instance
  """

  _resource_data: dict

  def __init__(self, project_id, resource_data):
    super().__init__(project_id=project_id)
    self._resource_data = resource_data

  @property
  def full_path(self) -> str:
    """
    The 'name' of the instance is already in the full path form
    projects/{project}/locations/{location}/instances/{instance}.
    """
    return self._resource_data[NAME_KEY]

  @property
  def short_path(self) -> str:
    path = self.full_path
    path = re.sub(r'^projects/', '', path)
    path = re.sub(r'/locations/', '/', path)
    path = re.sub(r'/instances/', '/', path)
    return path

  @property
  def metadata(self) -> dict:
    return self._resource_data.get('metadata', {})

  @property
  def name(self) -> str:
    logging.info(self._resource_data)
    return self._resource_data[NAME_KEY]


class Runtime(models.Resource):
  """Represent a Vertex AI Workbench runtime for a managed notebook instance

  https://cloud.google.com/vertex-ai/docs/workbench/reference/rest/v1/projects.locations.runtimes#resource:-runtime
  """

  _resource_data: dict

  def __init__(self, project_id, resource_data):
    super().__init__(project_id=project_id)
    self._resource_data = resource_data

  @property
  def full_path(self) -> str:
    """
    The 'name' of the runtime is already in the full path form
    projects/{project}/locations/{location}/runtimes/{instance}.
    """
    return self._resource_data[NAME_KEY]

  @property
  def short_path(self) -> str:
    path = self.full_path
    path = re.sub(r'^projects/', '', path)
    path = re.sub(r'/locations/', '/', path)
    path = re.sub(r'/runtimes/', '/', path)
    return path

  @property
  def metadata(self) -> dict:
    return self._resource_data.get('metadata', {})

  @property
  def name(self) -> str:
    logging.info(self._resource_data)
    return self._resource_data[NAME_KEY]

  @property
  def software_config(self) -> dict:
    return self._resource_data.get('softwareConfig', {})

  @property
  def idle_shutdown(self) -> bool:
    return self.software_config.get('idleShutdown', False)

  @property
  def is_upgradeable(self) -> bool:
    return self.software_config.get('upgradeable', False)

  @property
  def version(self) -> str:
    return self.software_config.get('version', '')

  @property
  def health_state(self) -> HealthStateEnum:
    return self._resource_data.get(HEALTH_STATE_KEY,
                                   HealthStateEnum.HEALTH_STATE_UNSPECIFIED)


@caching.cached_api_call
def get_instances(context: models.Context) -> Mapping[str, Instance]:
  instances: Dict[str, Instance] = {}
  logging.info(
      'fetching list of Vertex AI Workbench notebook instances in project %s',
      context.project_id)
  notebooks_api = apis.get_api('notebooks', 'v1', context.project_id)
  query = notebooks_api.projects().locations().instances().list(
      parent=f'projects/{context.project_id}/locations/-'
  )  #'-' (wildcard) all regions
  try:
    resp = query.execute(num_retries=config.API_RETRIES)
    if INSTANCES_KEY not in resp:
      return instances
    for i in resp[INSTANCES_KEY]:
      # verify that we have some minimal data that we expect
      if NAME_KEY not in i:
        raise RuntimeError(
            'missing instance name in projects.locations.instances.list response'
        )
      # projects/{projectId}/locations/{location}/instances/{instanceId}
      result = re.match(r'projects/[^/]+/locations/([^/]+)/instances/([^/]+)',
                        i['name'])
      if not result:
        logging.error('invalid notebook instances data: %s', i['name'])
        continue

      if not context.match_project_resource(location=result.group(1),
                                            resource=result.group(2),
                                            labels=i.get('labels', {})):
        continue
      instances[i[NAME_KEY]] = Instance(project_id=context.project_id,
                                        resource_data=i)
  except googleapiclient.errors.HttpError as err:
    raise utils.GcpApiError(err) from err
  return instances


@caching.cached_api_call
def _get_instance_health(context: models.Context, name: str) -> dict:
  logging.info(
      'fetching Vertex AI user-managed notebook instance health state in '
      'project %s', context.project_id)
  notebooks_api = apis.get_api('notebooks', 'v1', context.project_id)
  query = notebooks_api.projects().locations().instances().getInstanceHealth(
      name=name)
  return query.execute(num_retries=config.API_RETRIES)


def get_instance_health_info(context: models.Context, name: str) -> dict:
  try:
    return _get_instance_health(context, name).get(HEALTH_INFO_KEY, {})
  except googleapiclient.errors.HttpError as err:
    raise utils.GcpApiError(err) from err


def get_instance_health_state(context: models.Context,
                              name: str) -> HealthStateEnum:
  instance_health_state = HealthStateEnum('HEALTH_STATE_UNSPECIFIED')

  try:
    resp = _get_instance_health(context, name)
    if HEALTH_STATE_KEY not in resp:
      raise RuntimeError(
          'missing instance health state in projects.locations.instances:getInstanceHealth response'
      )
    instance_health_state = HealthStateEnum(resp[HEALTH_STATE_KEY])
    return instance_health_state
  except googleapiclient.errors.HttpError as err:
    raise utils.GcpApiError(err) from err
  return instance_health_state


@caching.cached_api_call
def get_runtimes(context: models.Context) -> Mapping[str, Runtime]:
  runtimes: Dict[str, Runtime] = {}
  if not apis.is_enabled(context.project_id, 'notebooks'):
    return runtimes
  logging.info(
      'fetching list of Vertex AI Workbench managed notebook runtimes in project %s',
      context.project_id)
  notebooks_api = apis.get_api('notebooks', 'v1', context.project_id)
  query = notebooks_api.projects().locations().runtimes().list(
      parent=f'projects/{context.project_id}/locations/-'
  )  #'-' (wildcard) all regions
  try:
    resp = query.execute(num_retries=config.API_RETRIES)
    if RUNTIMES_KEY not in resp:
      return runtimes
    for i in resp[RUNTIMES_KEY]:
      # verify that we have some minimal data that we expect
      if NAME_KEY not in i:
        raise RuntimeError(
            'missing runtime name in projects.locations.runtimes.list response')
      # projects/{projectId}/locations/{location}/runtimes/{runtimeId}
      result = re.match(r'projects/[^/]+/locations/([^/]+)/runtimes/([^/]+)',
                        i['name'])
      if not result:
        logging.error('invalid notebook runtimes data: %s', i['name'])
        continue

      if not context.match_project_resource(location=result.group(1),
                                            resource=result.group(2),
                                            labels=i.get('labels', {})):
        continue
      runtimes[i[NAME_KEY]] = Runtime(project_id=context.project_id,
                                      resource_data=i)
  except googleapiclient.errors.HttpError as err:
    raise utils.GcpApiError(err) from err
  return runtimes
