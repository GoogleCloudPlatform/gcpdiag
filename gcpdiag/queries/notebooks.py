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
from typing import Dict, Mapping, Union

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


class StateEnum(enum.Enum):
  """Vertex AI Workbench instance states

  https://cloud.google.com/vertex-ai/docs/workbench/reference/rest/v2/projects.locations.instances#state
  """

  STATE_UNSPECIFIED = 'STATE_UNSPECIFIED'
  STARTING = 'STARTING'
  PROVISIONING = 'PROVISIONING'
  ACTIVE = 'ACTIVE'
  STOPPING = 'STOPPING'
  STOPPED = 'STOPPED'
  DELETED = 'DELETED'
  UPGRADING = 'UPGRADING'
  INITIALIZING = 'INITIALIZING'
  SUSPENDING = 'SUSPENDING'
  SUSPENDED = 'SUSPENDED'

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


class WorkbenchInstance(Instance):
  """Represent a Vertex AI Workbench Instance

  https://cloud.google.com/vertex-ai/docs/workbench/reference/rest/v2/projects.locations.instances#Instance
  """

  _resource_data: dict

  def __init__(self, project_id, resource_data):
    super().__init__(project_id=project_id, resource_data=resource_data)
    self._resource_data = resource_data

  @property
  def state(self) -> StateEnum:
    return StateEnum[self._resource_data.get('state', 'STATE_UNSPECIFIED')]

  @property
  def gce_setup(self) -> dict:
    return self._resource_data.get('gceSetup', {})

  @property
  def gce_service_account_email(self) -> str:
    gce_setup_service_accounts = self.gce_setup.get('serviceAccounts', [])
    return gce_setup_service_accounts[0].get(
        'email', '') if len(gce_setup_service_accounts) > 0 else ''

  @property
  def network(self) -> str:
    gce_setup_network_interfaces = self.gce_setup.get('networkInterfaces', [])
    return gce_setup_network_interfaces[0].get(
        'network', '') if len(gce_setup_network_interfaces) > 0 else ''

  @property
  def subnet(self) -> str:
    gce_setup_network_interfaces = self.gce_setup.get('networkInterfaces', [])
    return gce_setup_network_interfaces[0].get(
        'subnet', '') if len(gce_setup_network_interfaces) > 0 else ''

  @property
  def disable_public_ip(self) -> bool:
    return self.gce_setup.get('disablePublicIp', False)

  @property
  def metadata(self) -> dict:
    # https://cloud.google.com/vertex-ai/docs/workbench/instances/manage-metadata#keys
    return self.gce_setup.get('metadata', {})

  @property
  def environment_version(self) -> int:
    return int(self.metadata.get('version', '0'))

  @property
  def disable_mixer(self) -> bool:
    return self.metadata.get('disable-mixer', '').lower() == 'true'

  @property
  def serial_port_logging_enabled(self) -> bool:
    return self.metadata.get('serial-port-logging-enable', '').lower() == 'true'

  @property
  def report_event_health(self) -> bool:
    return self.metadata.get('report-event-health', '').lower() == 'true'

  @property
  def post_startup_script(self) -> str:
    return self.metadata.get('post-startup-script', '')

  @property
  def startup_script(self) -> str:
    return self.metadata.get('startup-script', '')

  @property
  def startup_script_url(self) -> str:
    return self.metadata.get('startup-script-url', '')

  @property
  def health_state(self) -> HealthStateEnum:
    return self._resource_data.get(HEALTH_STATE_KEY,
                                   HealthStateEnum.HEALTH_STATE_UNSPECIFIED)

  @property
  def health_info(self) -> dict:
    return self._resource_data.get(HEALTH_INFO_KEY, {})

  @property
  def is_jupyterlab_status_healthy(self) -> bool:
    return self.health_info.get('jupyterlab_status', '') == '1'

  @property
  def is_jupyterlab_api_status_healthy(self) -> bool:
    return self.health_info.get('jupyterlab_api_status', '') == '1'

  @property
  def is_notebooks_api_dns_healthy(self) -> bool:
    return self.health_info.get('notebooks_api_dns', '') == '1'

  @property
  def is_proxy_registration_dns_healthy(self) -> bool:
    return self.health_info.get('proxy_registration_dns', '') == '1'

  @property
  def is_system_healthy(self) -> bool:
    return self.health_info.get('system_health', '') == '1'

  @property
  def is_docker_status_healthy(self) -> bool:
    return self.health_info.get('docker_status', '') == '1'

  @property
  def is_docker_proxy_agent_status_healthy(self) -> bool:
    return self.metadata.get('docker_proxy_agent_status', '') == '1'


@caching.cached_api_call
def get_instances(context: models.Context) -> Mapping[str, Instance]:
  instances: Dict[str, Instance] = {}
  if not apis.is_enabled(context.project_id, 'notebooks'):
    return instances
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
def instance_is_upgradeable(
    context: models.Context,
    notebook_instance: str) -> Dict[str, Union[str, bool]]:
  is_upgradeable: Dict[str, Union[str, bool]] = {}
  if not apis.is_enabled(context.project_id, 'notebooks'):
    logging.error('Notebooks API is not enabled')
    return is_upgradeable
  if not notebook_instance:
    logging.error('notebookInstance not provided')
    return is_upgradeable
  logging.info(
      'fetching Vertex AI user-managed notebook instance is upgradeable in project %s',
      context.project_id)
  notebooks_api = apis.get_api('notebooks', 'v1', context.project_id)
  query = notebooks_api.projects().locations().instances().isUpgradeable(
      notebookInstance=notebook_instance)
  try:
    resp = query.execute(num_retries=config.API_RETRIES)
    if 'upgradeable' not in resp:
      raise RuntimeError(
          'missing instance upgradeable data in projects.locations.instances:isUpgradeable response'
      )
    is_upgradeable = resp
    return is_upgradeable
  except googleapiclient.errors.HttpError as err:
    raise utils.GcpApiError(err) from err
  return is_upgradeable


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


@caching.cached_api_call
def get_workbench_instance(project_id: str, zone: str,
                           instance_name: str) -> Instance:
  """Returns workbench instance object matching instance name and zone
  https://cloud.google.com/vertex-ai/docs/workbench/reference/rest/v2/projects.locations.instances/get
  """
  workbench_instance: WorkbenchInstance = WorkbenchInstance(
      project_id=project_id, resource_data={})
  if not apis.is_enabled(project_id, 'notebooks'):
    return workbench_instance
  notebooks_api = apis.get_api('notebooks', 'v2', project_id)
  name = f'projects/{project_id}/locations/{zone}/instances/{instance_name}'
  query = notebooks_api.projects().locations().instances().get(name=name)
  try:
    response = query.execute(num_retries=config.API_RETRIES)
    workbench_instance = WorkbenchInstance(project_id=project_id,
                                           resource_data=response)
  except googleapiclient.errors.HttpError as err:
    raise utils.GcpApiError(err) from err
  return workbench_instance


@caching.cached_api_call
def workbench_instance_check_upgradability(
    project_id: str,
    workbench_instance_name: str) -> Dict[str, Union[str, bool]]:
  """Returns if workbench instance is upgradable and upgrade details
  https://cloud.google.com/vertex-ai/docs/workbench/reference/rest/v2/projects.locations.instances/checkUpgradability"""
  check_upgradability: Dict[str, Union[str, bool]] = {}
  if not apis.is_enabled(project_id, 'notebooks'):
    logging.error('Notebooks API is not enabled')
    return check_upgradability
  if not workbench_instance_name:
    logging.error('Workbench Instance name not provided')
    return check_upgradability
  logging.info(
      'fetching Vertex AI Workbench Instance is upgradeable in project %s',
      project_id)
  notebooks_api = apis.get_api('notebooks', 'v2', project_id)
  query = notebooks_api.projects().locations().instances().checkUpgradability(
      notebookInstance=workbench_instance_name)
  try:
    response = query.execute(num_retries=config.API_RETRIES)
    return response
  except googleapiclient.errors.HttpError as err:
    raise utils.GcpApiError(err) from err
  return check_upgradability
