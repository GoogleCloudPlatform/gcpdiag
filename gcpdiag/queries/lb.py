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

import googleapiclient

from gcpdiag import caching, config, models
from gcpdiag.queries import apis, apis_utils


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
  def timeout_sec(self) -> int:
    return self._resource_data.get('timeoutSec', None)

  @property
  def locality_lb_policy(self) -> str:
    return self._resource_data.get('localityLbPolicy', 'ROUND_ROBIN')

  @property
  def is_enable_cdn(self) -> str:
    return self._resource_data.get('enableCDN', False)

  @property
  def load_balancing_scheme(self) -> str:
    return self._resource_data.get('loadBalancingScheme', None)

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
  def backends(self) -> List[dict]:
    return self._resource_data.get('backends', [])

  @property
  def region(self):
    try:
      url = self._resource_data.get('region')
      if url is not None:
        match = re.search(r'/([^/]+)/?$', url)
        if match is not None:
          region = match.group(1)
          return region
        else:
          return None
    except KeyError:
      return None

  @property
  def used_by_refs(self) -> List[str]:
    used_by = []
    for x in self._resource_data.get('usedBy', []):
      reference = x.get('reference')
      if reference:
        match = re.match(r'https://www.googleapis.com/compute/v1/(.*)',
                         reference)
        if match:
          used_by.append(match.group(1))
    return used_by


@caching.cached_api_call(in_memory=True)
def get_backend_services(project_id: str) -> List[BackendServices]:
  logging.info('fetching Backend Services: %s', project_id)
  compute = apis.get_api('compute', 'v1', project_id)
  request = compute.backendServices().list(project=project_id)
  response = request.execute(num_retries=config.API_RETRIES)
  return [
      BackendServices(project_id, item) for item in response.get('items', [])
  ]


@caching.cached_api_call(in_memory=True)
def get_backend_service(project_id: str,
                        backend_service_name: str,
                        region: str = None) -> BackendServices:
  """Returns instance object matching backend service name and region"""
  compute = apis.get_api('compute', 'v1', project_id)
  if not region:
    request = compute.backendServices().get(project=project_id,
                                            backendService=backend_service_name)
  else:
    request = compute.regionBackendServices().get(
        project=project_id, region=region, backendService=backend_service_name)

  response = request.execute(num_retries=config.API_RETRIES)
  return BackendServices(project_id, resource_data=response)


class BackendHealth:
  """A Backend Service resource."""

  _resource_data: dict

  def __init__(self, resource_data, group):
    self._resource_data = resource_data
    self._group = group

  @property
  def instance(self) -> str:
    return self._resource_data['instance']

  @property
  def group(self) -> str:
    return self._group

  @property
  def health_state(self) -> str:
    return self._resource_data.get('healthState', 'UNHEALTHY')


def _generate_health_response_callback(
    backend_heath_statuses: List[BackendHealth], group: str):

  def health_response_callback(request_id, response, exception):
    del request_id, exception

    # None is returned when backend type doesn't support health check
    if response is not None:
      for health_status in response.get('healthStatus', []):
        backend_heath_statuses.append(BackendHealth(health_status, group))

  return health_response_callback


@caching.cached_api_call(in_memory=True)
def get_backend_service_health(
    project_id: str,
    backend_service_name: str,
    backend_service_region: str = None,
) -> List[BackendHealth]:
  """Returns health data for backend service."""
  try:
    backend_service = get_backend_service(project_id, backend_service_name,
                                          backend_service_region)
  except googleapiclient.errors.HttpError:
    return []

  backend_heath_statuses: List[BackendHealth] = []

  compute = apis.get_api('compute', 'v1', project_id)
  batch = compute.new_batch_http_request()

  for i, backend in enumerate(backend_service.backends):
    group = backend['group']
    if not backend_service.region:
      batch.add(
          compute.backendServices().getHealth(
              project=project_id,
              backendService=backend_service.name,
              body={'group': group},
          ),
          request_id=str(i),
          callback=_generate_health_response_callback(backend_heath_statuses,
                                                      group),
      )
    else:
      batch.add(
          compute.regionBackendServices().getHealth(
              project=project_id,
              region=backend_service.region,
              backendService=backend_service.name,
              body={'group': group},
          ),
          request_id=str(i),
          callback=_generate_health_response_callback(backend_heath_statuses,
                                                      group),
      )
  batch.execute()

  return backend_heath_statuses


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
  def global_access_allowed(self) -> bool:
    return self._resource_data.get('allowGlobalAccess', False)

  @property
  def load_balancing_scheme(self) -> str:
    return self._resource_data.get('loadBalancingScheme', None)


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


class LoadBalancerInsight(models.Resource):
  """Represents a Load Balancer Insights object"""

  @property
  def full_path(self) -> str:
    return self._resource_data['name']

  @property
  def description(self) -> str:
    return self._resource_data['description']

  @property
  def insight_subtype(self) -> str:
    return self._resource_data['insightSubtype']

  @property
  def details(self) -> dict:
    return self._resource_data['content']

  @property
  def is_firewall_rule_insight(self) -> bool:
    firewall_rule_subtypes = (
        'HEALTH_CHECK_FIREWALL_NOT_CONFIGURED',
        'HEALTH_CHECK_FIREWALL_FULLY_BLOCKING',
        'HEALTH_CHECK_FIREWALL_PARTIALLY_BLOCKING',
        'HEALTH_CHECK_FIREWALL_INCONSISTENT',
    )
    return self.insight_subtype.startswith(firewall_rule_subtypes)

  @property
  def is_health_check_port_mismatch_insight(self) -> bool:
    return self.insight_subtype == 'HEALTH_CHECK_PORT_MISMATCH'

  def __init__(self, project_id, resource_data):
    super().__init__(project_id=project_id)
    self._resource_data = resource_data


@caching.cached_api_call
def get_lb_insights_for_a_project(project_id: str, region: str = 'global'):
  api = apis.get_api('recommender', 'v1', project_id)

  insight_name = (f'projects/{project_id}/locations/{region}/insightTypes/'
                  'google.networkanalyzer.networkservices.loadBalancerInsight')
  insights = []
  for insight in apis_utils.list_all(
      request=api.projects().locations().insightTypes().insights().list(
          parent=insight_name),
      next_function=api.projects().locations().insightTypes().insights().
      list_next,
      response_keyword='insights',
  ):
    insights.append(LoadBalancerInsight(project_id, insight))
  return insights
