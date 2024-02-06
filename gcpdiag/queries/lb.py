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
"""Queries related to load balancer."""

import logging
import re
from typing import List

from gcpdiag import caching, config, models
from gcpdiag.queries import apis


class BackendServices(models.Resource):
  """A Backend Service resource."""

  _resource_data: dict
  _type: str

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
  def session_affinity(self) -> str:
    return self._resource_data.get('sessionAffinity', 'NONE')

  @property
  def locality_lb_policy(self) -> str:
    return self._resource_data.get('localityLbPolicy', 'ROUND_ROBIN')

  @property
  def is_enable_cdn(self) -> str:
    return self._resource_data.get('enableCDN', False)

  @property
  def load_balancing_scheme(self) -> str:
    return self._resource_data.get('loadBalancingScheme', 'NONE')

  @property
  def health_check(self) -> str:
    health_check_url = self._resource_data['healthChecks'][0]
    matches = re.search(r'/([^/]+)$', health_check_url)
    if matches:
      healthcheck_name = matches.group(1)
      return healthcheck_name
    else:
      return ''

  @property
  def region(self):
    try:
      url = self._resource_data.get('region', 'NONE')
      if url is not None:
        match = re.search(r'/([^/]+)/?$', url)
        if match is not None:
          region = match.group(1)
          return region
        else:
          return 'None'
    except KeyError:
      return 'None'


@caching.cached_api_call(in_memory=True)
def get_backend_services(project_id: str) -> List[BackendServices]:
  logging.info('fetching Backend Services: %s', project_id)
  compute = apis.get_api('compute', 'v1', project_id)
  request = compute.backendServices().list(project=project_id)
  response = request.execute(num_retries=config.API_RETRIES)
  return [
      BackendServices(project_id, item) for item in response.get('items', [])
  ]


class ForwardingRules(models.Resource):
  """A Forwarding Rule resource."""
  _resource_data: dict
  _type: str

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
  def is_global_access_allowed(self) -> bool:
    return self._resource_data.get('allowGlobalAccess', False)


@caching.cached_api_call(in_memory=True)
def get_forwarding_rules(project_id: str) -> List[ForwardingRules]:
  logging.info('fetching Forwarding Rules: %s', project_id)
  compute = apis.get_api('compute', 'v1', project_id)
  forwarding_rules = []
  request = compute.forwardingRules().aggregatedList(project=project_id)
  response = request.execute(num_retries=config.API_RETRIES)
  forwarding_rules_by_region = response['items']
  for _, data_ in forwarding_rules_by_region.items():
    if 'forwardingRules' not in data_:
      continue
    forwarding_rules.extend([
        ForwardingRules(project_id, forwarding_rule)
        for forwarding_rule in data_['forwardingRules']
    ])
  return forwarding_rules
