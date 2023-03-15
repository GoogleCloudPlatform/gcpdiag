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
 https://cloud.google.com/network-connectivity/docs/interconnect/apis
 """
  _resource_data: dict
  _type: str
  _attachments: List[str]

  def __init__(self, project_id, resource_data):
    super().__init__(project_id=project_id)
    self._resource_data = resource_data

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


@caching.cached_api_call(in_memory=True)
def get_interconnect(project_id: str, interconnect_name: str) -> Interconnect:
  logging.info('fetching interconnect: %s/%s', project_id, interconnect_name)
  compute = apis.get_api('compute', 'v1', project_id)
  request = compute.interconnects().get(project=project_id,
                                        interconnect=interconnect_name)
  response = request.execute(num_retries=config.API_RETRIES)
  return Interconnect(project_id, response)
