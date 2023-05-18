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
"""Queries related to CloudSQL."""

import ipaddress
from typing import Iterable

from boltons.iterutils import get_path

from gcpdiag import caching, config, models
from gcpdiag.queries import apis


class Instance(models.Resource):
  """ Represents CloudSQL Instnace"""
  _resource_data: dict

  def __init__(self, project_id: str, resource_data: dict):
    super().__init__(project_id)
    self._resource_data = resource_data

  @property
  def name(self) -> str:
    return self._resource_data['name']

  @property
  def status(self) -> str:
    return self._resource_data['state']

  @property
  def version(self) -> str:
    return self._resource_data['databaseVersion']

  @property
  def is_regional(self) -> bool:
    return get_path(self._resource_data, ('settings', 'availabilityType'),
                    default='ZONAL') == 'REGIONAL'

  @property
  def ip_addresses(self) -> Iterable[ipaddress.IPv4Address]:
    return [
        ipaddress.ip_address(nic['ipAddress'])
        for nic in self._resource_data.get('ipAddresses', [])
    ]

  @property
  def has_public_ip(self) -> bool:
    return get_path(self._resource_data,
                    ('settings', 'ipConfiguration', 'ipv4Enabled'))

  @property
  def has_maintenance_window(self) -> int:
    return get_path(self._resource_data,
                    ('settings', 'maintenanceWindow', 'day'))

  @property
  def self_link(self) -> str:
    return self._resource_data['selfLink']

  @property
  def full_path(self) -> str:
    return self.self_link

  def __str__(self) -> str:
    return self.self_link


@caching.cached_api_call
def get_instances(context: models.Context) -> Iterable[Instance]:
  if not apis.is_enabled(context.project_id, 'sqladmin'):
    return []

  api = apis.get_api('sqladmin', 'v1', context.project_id)
  query = api.instances().list(project=context.project_id)
  resp = query.execute(num_retries=config.API_RETRIES)
  databases = []
  for d in resp.get('items', []):
    location = d.get('region', '')
    labels = d.get('userLabels', {})
    resource = d.get('name', '')
    if not context.match_project_resource(
        location=location, labels=labels, resource=resource):
      continue

    databases.append(Instance(context.project_id, d))
  return databases
