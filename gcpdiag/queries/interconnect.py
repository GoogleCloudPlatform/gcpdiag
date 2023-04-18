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
"""Queries related to interconnects."""

import logging
import re
from typing import List

from gcpdiag import caching, config, models
from gcpdiag.queries import apis


class Interconnect(models.Resource):
  """Represents an Interconnect.
 https://cloud.google.com/compute/docs/reference/rest/v1/interconnects
 """
  _resource_data: dict
  _ead: str

  def __init__(self, project_id, resource_data):
    super().__init__(project_id=project_id)
    self._resource_data = resource_data
    self._ead = ''

  @property
  def name(self) -> str:
    return self._resource_data['name']

  @property
  def id(self) -> str:
    return self._resource_data['id']

  @property
  def full_path(self) -> str:
    result = re.match(r'https://www.googleapis.com/compute/v1/(.*)',
                      self.self_link)
    if result:
      return result.group(1)
    else:
      return f'>> {self.self_link}'

  @property
  def short_path(self) -> str:
    path = self.project_id + '/' + self.name
    return path

  @property
  def self_link(self) -> str:
    return self._resource_data['selfLink']

  @property
  def attachments(self) -> str:
    return self._resource_data['interconnectAttachments']

  @property
  def ead(self) -> str:
    if not self._ead:
      self._ead = self._resource_data['location'].split('/')[-1]
    return self._ead

  @property
  def metro(self) -> str:
    return _metro(self.ead)


@caching.cached_api_call(in_memory=True)
def get_interconnect(project_id: str, interconnect_name: str) -> Interconnect:
  logging.info('fetching interconnect: %s/%s', project_id, interconnect_name)
  compute = apis.get_api('compute', 'v1', project_id)
  request = compute.interconnects().get(project=project_id,
                                        interconnect=interconnect_name)
  response = request.execute(num_retries=config.API_RETRIES)
  return Interconnect(project_id, response)


@caching.cached_api_call(in_memory=True)
def get_interconnects(project_id: str) -> List[Interconnect]:
  logging.info('fetching interconnects: %s', project_id)
  compute = apis.get_api('compute', 'v1', project_id)
  request = compute.interconnects().list(project=project_id)
  response = request.execute(num_retries=config.API_RETRIES)
  return [Interconnect(project_id, link) for link in response]


def _metro(ead: str) -> str:
  return ead.split('-')[0]


class VlanAttachment(models.Resource):
  """Represents an Interconnect.
 https://cloud.google.com/compute/docs/reference/rest/v1/interconnectAttachments
 """
  _resource_data: dict
  _type: str
  _interconnect: str
  _ead: str

  def __init__(self, project_id, resource_data):
    super().__init__(project_id=project_id)
    self._resource_data = resource_data
    self._type = ''
    self._interconnect = ''
    self._ead = ''

  @property
  def name(self) -> str:
    return self._resource_data['name']

  @property
  def id(self) -> str:
    return self._resource_data['id']

  @property
  def full_path(self) -> str:
    result = re.match(r'https://www.googleapis.com/compute/v1/(.*)',
                      self.self_link)
    if result:
      return result.group(1)
    else:
      return f'>> {self.self_link}'

  @property
  def short_path(self) -> str:
    path = self.project_id + '/' + self.name
    return path

  @property
  def self_link(self) -> str:
    return self._resource_data['selfLink']

  @property
  def type(self) -> str:
    return self._resource_data['type']

  @property
  def interconnect(self) -> str:
    if not self._interconnect:
      self._interconnect = self._resource_data['interconnect'].split('/')[-1]
    return self._interconnect

  @property
  def ead(self) -> str:
    if not self._ead:
      interconnect_obj = get_interconnect(self.project_id, self.interconnect)
      self._ead = interconnect_obj.ead
    return self._ead

  @property
  def metro(self) -> str:
    return _metro(self.ead)


@caching.cached_api_call(in_memory=True)
def get_vlan_attachment(project_id: str, region: str,
                        vlan_attachment: str) -> VlanAttachment:
  logging.info('fetching attachment: %s/%s', project_id, vlan_attachment)
  compute = apis.get_api('compute', 'v1', project_id)
  request = compute.interconnectAttachments().get(
      project=project_id, region=region, interconnectAttachment=vlan_attachment)
  response = request.execute(num_retries=config.API_RETRIES)
  return VlanAttachment(project_id, response)


@caching.cached_api_call(in_memory=True)
def get_vlan_attachments(project_id: str) -> List[VlanAttachment]:
  logging.info('fetching attachments: %s', project_id)
  compute = apis.get_api('compute', 'v1', project_id)
  request = compute.interconnectAttachments().list(project=project_id)
  response = request.execute(num_retries=config.API_RETRIES)
  return [VlanAttachment(project_id, attachment) for attachment in response]
