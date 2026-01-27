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
"""Queries related to VPN tunnel."""

import logging
import re
from typing import List

from googleapiclient import errors as googleapiclient_errors

from gcpdiag import caching, config, models, utils
from gcpdiag.queries import apis


class Vpn(models.Resource):
  """
  Represents a Vpn Tunnel.
  https://cloud.google.com/compute/docs/reference/rest/v1/vpnTunnels
  """
  _resource_data: dict

  def __init__(self, project_id, resource_data):
    super().__init__(project_id=project_id)
    self._resource_data = resource_data

  @property
  def name(self) -> str:
    return self._resource_data['name']

  @property
  def under_maintenance(self) -> bool:
    return self._resource_data.get('status') == 'UNDER_MAINTENANCE'

  @property
  def peer_ip(self) -> str:
    return self._resource_data['peerIp']

  @property
  def status(self) -> str:
    return self._resource_data['status']

  @property
  def router(self) -> str:
    return self._resource_data['router']

  @property
  def id(self) -> str:
    return self._resource_data['id']

  @property
  def local_traffic_selector(self) -> List[str]:
    return self._resource_data.get('localTrafficSelector', [])

  @property
  def remote_traffic_selector(self) -> List[str]:
    return self._resource_data.get('remoteTrafficSelector', [])

  @property
  def self_link(self) -> str:
    return self._resource_data['selfLink']

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


@caching.cached_api_call(in_memory=True)
def get_vpn(project_id: str, vpn_name: str, region: str) -> Vpn:
  logging.debug('fetching VPN: %s', vpn_name)
  compute = apis.get_api('compute', 'v1', project_id)

  request = compute.vpnTunnels().get(project=project_id,
                                     vpnTunnel=vpn_name,
                                     region=region)
  try:
    response = request.execute(num_retries=config.API_RETRIES)
  except googleapiclient_errors.HttpError as err:
    raise utils.GcpApiError(err)
  return Vpn(project_id, response)
