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
"""Queries related to Data Fusion."""

import ipaddress
import logging
import re
from typing import Dict, Mapping

import googleapiclient.errors

from gcpdiag import caching, config, models, utils
from gcpdiag.queries import apis, network


class Instance(models.Resource):
  """Represents a Data Fusion instance.

  https://cloud.google.com/data-fusion/docs/reference/rest/v1/projects.locations.instances#Instance
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
    return self._resource_data['name']

  @property
  def short_path(self) -> str:
    path = self.full_path
    path = re.sub(r'^projects/', '', path)
    path = re.sub(r'/locations/', '/', path)
    path = re.sub(r'/instances/', '/', path)
    return path

  @property
  def name(self) -> str:
    return utils.extract_value_from_res_name(self._resource_data['name'],
                                             'instances')

  @property
  def location(self) -> str:
    return utils.extract_value_from_res_name(self._resource_data['name'],
                                             'locations')

  @property
  def zone(self) -> str:
    return self._resource_data['zone']

  @property
  def type(self) -> str:
    return self._resource_data['type']

  @property
  def is_basic_type(self) -> bool:
    return self._resource_data['type'] == 'BASIC'

  @property
  def is_enterprise_type(self) -> bool:
    return self._resource_data['type'] == 'ENTERPRISE'

  @property
  def is_developer_type(self) -> bool:
    return self._resource_data['type'] == 'DEVELOPER'

  @property
  def is_private(self) -> bool:
    return self._resource_data['privateInstance']

  @property
  def status(self) -> str:
    return self._resource_data['state']

  @property
  def is_running(self) -> bool:
    return self.status == 'ACTIVE'

  @property
  def is_deleting(self) -> bool:
    return self._resource_data['state'] == 'DELETING'

  @property
  def version(self) -> str:
    return self._resource_data['version']

  @property
  def api_service_agent(self) -> str:
    return self._resource_data['p4ServiceAccount']

  @property
  def dataproc_service_account(self) -> str:
    return self._resource_data['dataprocServiceAccount']

  @property
  def tenant_project_id(self) -> str:
    return self._resource_data['tenantProjectId']

  @property
  def uses_shared_vpc(self) -> bool:
    """
    If shared VPC then 'network_string' = 'projects/{host-project-id}/global/networks/{network}'
    else 'network_string' = {network}
    """
    network_string = self._resource_data['networkConfig']['network']
    match = re.match(r'projects/([^/]+)/global/networks/([^/]+)$',
                     network_string)
    if match and match.group(1) != self.project_id:
      return True

    return False

  @property
  def network(self) -> network.Network:
    network_string = self._resource_data['networkConfig']['network']
    match = re.match(r'projects/([^/]+)/global/networks/([^/]+)$',
                     network_string)
    if match:
      return network.get_network(match.group(1), match.group(2))
    else:
      return network.get_network(self.project_id, network_string)

  @property
  def tp_ipv4_cidr(self) -> ipaddress.IPv4Network:
    cidr = self._resource_data['networkConfig']['ipAllocation']
    return ipaddress.ip_network(cidr)


@caching.cached_api_call
def get_instances(context: models.Context) -> Mapping[str, Instance]:
  """Get a dict of Instance matching the given context, indexed by instance full path."""
  instances: Dict[str, Instance] = {}

  if not apis.is_enabled(context.project_id, 'datafusion'):
    return instances

  logging.info('fetching list of Data Fusion instances in project %s',
               context.project_id)
  datafusion_api = apis.get_api('datafusion', 'v1', context.project_id)
  query = datafusion_api.projects().locations().instances().list(
      parent=f'projects/{context.project_id}/locations/-'
  )  #'-' (wildcard) all regions

  try:
    resp = query.execute(num_retries=config.API_RETRIES)
    if 'instances' not in resp:
      return instances

    for resp_i in resp['instances']:
      # verify that we have some minimal data that we expect
      if 'name' not in resp_i:
        raise RuntimeError(
            'missing instance name in projects.locations.instances.list response'
        )

      i = Instance(project_id=context.project_id, resource_data=resp_i)
      instances[i.full_path] = i

  except googleapiclient.errors.HttpError as err:
    raise utils.GcpApiError(err) from err

  return instances
