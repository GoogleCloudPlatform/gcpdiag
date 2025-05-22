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
from enum import Enum
from typing import Dict, List, Literal, Optional

import googleapiclient

from gcpdiag import caching, config, models
from gcpdiag.queries import apis, apis_utils


class LoadBalancerType(Enum):
  """Load balancer type."""

  LOAD_BALANCER_TYPE_UNSPECIFIED = 0
  EXTERNAL_PASSTHROUGH_LB = 1
  INTERNAL_PASSTHROUGH_LB = 2
  TARGET_POOL_LB = 3  # deprecated but customers still have them
  GLOBAL_EXTERNAL_PROXY_NETWORK_LB = 4  # envoy based proxy lb
  REGIONAL_INTERNAL_PROXY_NETWORK_LB = 5
  REGIONAL_EXTERNAL_PROXY_NETWORK_LB = 6
  CROSS_REGION_INTERNAL_PROXY_NETWORK_LB = 7
  CLASSIC_PROXY_NETWORK_LB = 8
  GLOBAL_EXTERNAL_APPLICATION_LB = 9  # envoy based application lb
  REGIONAL_INTERNAL_APPLICATION_LB = 10
  REGIONAL_EXTERNAL_APPLICATION_LB = 11
  CROSS_REGION_INTERNAL_APPLICATION_LB = 12
  CLASSIC_APPLICATION_LB = 13


def get_load_balancer_type_name(lb_type: LoadBalancerType) -> str:
  """Returns a human-readable name for the given load balancer type."""

  type_names = {
      LoadBalancerType.LOAD_BALANCER_TYPE_UNSPECIFIED:
          'Unspecified',
      LoadBalancerType.EXTERNAL_PASSTHROUGH_LB:
          ('External Passthrough Network Load Balancer'),
      LoadBalancerType.INTERNAL_PASSTHROUGH_LB:
          ('Internal Passthrough Network Load Balancer'),
      LoadBalancerType.TARGET_POOL_LB:
          'Target Pool Network Load Balancer',
      LoadBalancerType.GLOBAL_EXTERNAL_PROXY_NETWORK_LB:
          ('Global External Proxy Network Load Balancer'),
      LoadBalancerType.REGIONAL_INTERNAL_PROXY_NETWORK_LB:
          ('Regional Internal Proxy Network Load Balancer'),
      LoadBalancerType.REGIONAL_EXTERNAL_PROXY_NETWORK_LB:
          ('Regional External Proxy Network Load Balancer'),
      LoadBalancerType.CROSS_REGION_INTERNAL_PROXY_NETWORK_LB:
          ('Cross-Region Internal Proxy Network Load Balancer'),
      LoadBalancerType.CLASSIC_PROXY_NETWORK_LB:
          ('Classic Proxy Network Load Balancer'),
      LoadBalancerType.GLOBAL_EXTERNAL_APPLICATION_LB:
          ('Global External Application Load Balancer'),
      LoadBalancerType.REGIONAL_INTERNAL_APPLICATION_LB:
          ('Regional Internal Application Load Balancer'),
      LoadBalancerType.REGIONAL_EXTERNAL_APPLICATION_LB:
          ('Regional External Application Load Balancer'),
      LoadBalancerType.CROSS_REGION_INTERNAL_APPLICATION_LB:
          ('Cross-Region Internal Application Load Balancer'),
      LoadBalancerType.CLASSIC_APPLICATION_LB:
          ('Classic Application Load Balancer'),
  }
  return type_names.get(lb_type, 'Unspecified')


def get_load_balancer_type(
    load_balancing_scheme: str,
    scope: str,
    layer: Literal['application', 'network'],
    backend_service_based: bool = True,
) -> LoadBalancerType:
  if load_balancing_scheme == 'EXTERNAL':
    if not scope or scope == 'global':
      if layer == 'application':
        return LoadBalancerType.CLASSIC_APPLICATION_LB
      else:
        return LoadBalancerType.CLASSIC_PROXY_NETWORK_LB
    else:
      return (LoadBalancerType.EXTERNAL_PASSTHROUGH_LB
              if backend_service_based else LoadBalancerType.TARGET_POOL_LB)
  elif load_balancing_scheme == 'INTERNAL':
    return LoadBalancerType.INTERNAL_PASSTHROUGH_LB
  elif load_balancing_scheme == 'INTERNAL_MANAGED':
    if not scope or scope == 'global':
      if layer == 'application':
        return LoadBalancerType.CROSS_REGION_INTERNAL_APPLICATION_LB
      else:
        return LoadBalancerType.CROSS_REGION_INTERNAL_PROXY_NETWORK_LB
    else:
      if layer == 'application':
        return LoadBalancerType.REGIONAL_INTERNAL_APPLICATION_LB
      else:
        return LoadBalancerType.REGIONAL_INTERNAL_PROXY_NETWORK_LB
  elif load_balancing_scheme == 'EXTERNAL_MANAGED':
    if not scope or scope == 'global':
      if layer == 'application':
        return LoadBalancerType.GLOBAL_EXTERNAL_APPLICATION_LB
      else:
        return LoadBalancerType.GLOBAL_EXTERNAL_PROXY_NETWORK_LB
    else:
      if layer == 'application':
        return LoadBalancerType.REGIONAL_EXTERNAL_APPLICATION_LB
      else:
        return LoadBalancerType.REGIONAL_EXTERNAL_PROXY_NETWORK_LB
  return LoadBalancerType.LOAD_BALANCER_TYPE_UNSPECIFIED


def normalize_url(url: str) -> str:
  """Returns normalized url."""
  result = re.match(r'https://www.googleapis.com/compute/v1/(.*)', url)
  if result:
    return result.group(1)
  else:
    return ''


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
  def draining_timeout_sec(self) -> int:
    return self._resource_data.get('connectionDraining',
                                   {}).get('drainingTimeoutSec', 0)

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
  def protocol(self) -> str:
    return self._resource_data.get('protocol', None)

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

  @property
  def load_balancer_type(self) -> LoadBalancerType:
    application_protocols = ['HTTP', 'HTTPS', 'HTTP2']
    return get_load_balancer_type(
        self.load_balancing_scheme,
        self.region,
        'application' if self.protocol in application_protocols else 'network',
        backend_service_based=True,
    )


@caching.cached_api_call(in_memory=True)
def get_backend_services(project_id: str) -> List[BackendServices]:
  logging.debug('fetching Backend Services: %s', project_id)
  compute = apis.get_api('compute', 'v1', project_id)
  backend_services = []
  request = compute.backendServices().aggregatedList(project=project_id)
  response = request.execute(num_retries=config.API_RETRIES)
  backend_services_by_region = response['items']
  for _, data_ in backend_services_by_region.items():
    if 'backendServices' not in data_:
      continue
    backend_services.extend([
        BackendServices(project_id, backend_service)
        for backend_service in data_['backendServices']
    ])
  return backend_services


@caching.cached_api_call(in_memory=True)
def get_backend_service(project_id: str,
                        backend_service_name: str,
                        region: str = None) -> BackendServices:
  """Returns instance object matching backend service name and region"""
  compute = apis.get_api('compute', 'v1', project_id)
  if not region or region == 'global':
    request = compute.backendServices().get(project=project_id,
                                            backendService=backend_service_name)
  else:
    request = compute.regionBackendServices().get(
        project=project_id, region=region, backendService=backend_service_name)

  response = request.execute(num_retries=config.API_RETRIES)
  return BackendServices(project_id, resource_data=response)


def get_backend_service_by_self_link(
    backend_service_self_link: str,) -> Optional[BackendServices]:
  backend_service_name = backend_service_self_link.split('/')[-1]
  backend_service_scope = backend_service_self_link.split('/')[-3]
  match = re.match(r'projects/([^/]+)/', backend_service_self_link)
  if not match:
    return None
  project_id = match.group(1)
  return get_backend_service(project_id, backend_service_name,
                             backend_service_scope)


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

  for backend in backend_service.backends:
    group = backend['group']
    if not backend_service.region:
      response = compute.backendServices().getHealth(
          project=project_id,
          backendService=backend_service.name,
          body={
              'group': group
          },
      ).execute(num_retries=config.API_RETRIES)
      # None is returned when backend type doesn't support health check
      if response is not None:
        for health_status in response.get('healthStatus', []):
          backend_heath_statuses.append(BackendHealth(health_status, group))
    else:
      response = compute.regionBackendServices().getHealth(
          project=project_id,
          region=backend_service.region,
          backendService=backend_service.name,
          body={
              'group': group
          },
      ).execute(num_retries=config.API_RETRIES)
      if response is not None:
        for health_status in response.get('healthStatus', []):
          backend_heath_statuses.append(BackendHealth(health_status, group))

  return backend_heath_statuses


class SslCertificate(models.Resource):
  """A SSL Certificate resource."""

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
  def self_link(self) -> str:
    return self._resource_data['selfLink']

  @property
  def type(self) -> str:
    return self._resource_data.get('type', 'SELF_MANAGED')

  @property
  def status(self) -> str:
    return self._resource_data.get('managed', {}).get('status')

  @property
  def domains(self) -> List[str]:
    return self._resource_data.get('managed', {}).get('domains', [])

  @property
  def domain_status(self) -> Dict[str, str]:
    return self._resource_data.get('managed', {}).get('domainStatus', {})


@caching.cached_api_call(in_memory=True)
def get_ssl_certificate(
    project_id: str,
    certificate_name: str,
) -> SslCertificate:
  """Returns object matching certificate name and region"""
  compute = apis.get_api('compute', 'v1', project_id)

  request = compute.sslCertificates().get(project=project_id,
                                          sslCertificate=certificate_name)

  response = request.execute(num_retries=config.API_RETRIES)
  return SslCertificate(project_id, resource_data=response)


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
  def region(self):
    url = self._resource_data.get('region', '')
    if url is not None:
      match = re.search(r'/([^/]+)/?$', url)
      if match is not None:
        region = match.group(1)
        return region
    return 'global'

  @property
  def self_link(self) -> str:
    return self._resource_data['selfLink']

  @property
  def global_access_allowed(self) -> bool:
    return self._resource_data.get('allowGlobalAccess', False)

  @property
  def load_balancing_scheme(self) -> str:
    return self._resource_data.get('loadBalancingScheme', None)

  @property
  def target(self) -> str:
    full_path = self._resource_data.get('target', '')
    result = re.match(r'https://www.googleapis.com/compute/v1/(.*)', full_path)
    if result:
      return result.group(1)
    else:
      return ''

  @property
  def backend_service(self) -> str:
    full_path = self._resource_data.get('backendService', '')
    result = re.match(r'https://www.googleapis.com/compute/v1/(.*)', full_path)
    if result:
      return result.group(1)
    else:
      return ''

  @property
  def ip_address(self) -> str:
    return self._resource_data.get('IPAddress', '')

  @property
  def port_range(self) -> str:
    return self._resource_data.get('portRange', '')

  @caching.cached_api_call(in_memory=True)
  def get_related_backend_services(self) -> List[BackendServices]:
    """Returns the backend services related to the forwarding rule."""
    if self.backend_service:
      resource = get_backend_service_by_self_link(self.backend_service)
      return [resource] if resource else []
    if self.target:
      target_proxy_target = get_target_proxy_reference(self.target)
      if not target_proxy_target:
        return []
      target_proxy_target_type = target_proxy_target.split('/')[-2]
      if target_proxy_target_type == 'backendServices':
        resource = get_backend_service_by_self_link(target_proxy_target)
        return [resource] if resource else []
      elif target_proxy_target_type == 'urlMaps':
        # Currently it doesn't work for shared-vpc backend services
        backend_services = get_backend_services(self.project_id)
        return [
            backend_service for backend_service in backend_services
            if target_proxy_target in backend_service.used_by_refs
        ]
    return []

  @property
  def load_balancer_type(self) -> LoadBalancerType:
    target_type = None
    if self.target:
      parts = self.target.split('/')
      if len(parts) >= 2:
        target_type = parts[-2]

    application_targets = [
        'targetHttpProxies',
        'targetHttpsProxies',
        'targetGrpcProxies',
    ]

    return get_load_balancer_type(
        self.load_balancing_scheme,
        self.region,
        'application' if target_type in application_targets else 'network',
        target_type != 'targetPools',
    )


@caching.cached_api_call(in_memory=True)
def get_target_proxy_reference(target_proxy_self_link: str) -> str:
  """Retrieves the URL map or backend service associated with a given target proxy.

  Args:
    target_proxy_self_link: self link of the target proxy

  Returns:
    The url map or the backend service self link
  """
  target_proxy_type = target_proxy_self_link.split('/')[-2]
  target_proxy_name = target_proxy_self_link.split('/')[-1]
  target_proxy_scope = target_proxy_self_link.split('/')[-3]
  match_result = re.match(r'projects/([^/]+)/', target_proxy_self_link)
  if not match_result:
    return ''
  project_id = match_result.group(1)
  compute = apis.get_api('compute', 'v1', project_id)

  request = None
  if target_proxy_type == 'targetHttpsProxies':
    if target_proxy_scope == 'global':
      request = compute.targetHttpsProxies().get(
          project=project_id, targetHttpsProxy=target_proxy_name)
    else:
      request = compute.regionTargetHttpsProxies().get(
          project=project_id,
          region=target_proxy_scope,
          targetHttpsProxy=target_proxy_name,
      )
  elif target_proxy_type == 'targetHttpProxies':
    if target_proxy_scope == 'global':
      request = compute.targetHttpProxies().get(
          project=project_id, targetHttpProxy=target_proxy_name)
    else:
      request = compute.regionTargetHttpProxies().get(
          project=project_id,
          region=target_proxy_scope,
          targetHttpProxy=target_proxy_name,
      )
  elif target_proxy_type == 'targetTcpProxies':
    if target_proxy_scope == 'global':
      request = compute.targetTcpProxies().get(project=project_id,
                                               targetTcpProxy=target_proxy_name)
    else:
      request = compute.regionTargetTcpProxies().get(
          project=project_id,
          region=target_proxy_scope,
          targetTcpProxy=target_proxy_name,
      )
  elif target_proxy_type == 'targetSslProxies':
    request = compute.targetSslProxies().get(project=project_id,
                                             targetSslProxy=target_proxy_name)
  elif target_proxy_type == 'targetGrcpProxies':
    request = compute.targetGrpcProxies().get(project=project_id,
                                              targetGrpcProxy=target_proxy_name)
  if not request:
    # target is not target proxy
    return ''
  response = request.execute(num_retries=config.API_RETRIES)
  if 'urlMap' in response:
    return normalize_url(response['urlMap'])
  if 'service' in response:
    return normalize_url(response['service'])
  return ''


@caching.cached_api_call(in_memory=True)
def get_forwarding_rules(project_id: str) -> List[ForwardingRules]:
  logging.debug('fetching Forwarding Rules: %s', project_id)
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


@caching.cached_api_call(in_memory=True)
def get_forwarding_rule(project_id: str,
                        forwarding_rule_name: str,
                        region: str = None) -> ForwardingRules:
  compute = apis.get_api('compute', 'v1', project_id)
  if not region or region == 'global':
    request = compute.globalForwardingRules().get(
        project=project_id, forwardingRule=forwarding_rule_name)
  else:
    request = compute.forwardingRules().get(project=project_id,
                                            region=region,
                                            forwardingRule=forwarding_rule_name)
  response = request.execute(num_retries=config.API_RETRIES)
  return ForwardingRules(project_id, resource_data=response)


class TargetHttpsProxy(models.Resource):
  """A Target HTTPS Proxy resource."""

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
  def self_link(self) -> str:
    return self._resource_data['selfLink']

  @property
  def region(self):
    url = self._resource_data.get('region', '')
    if url is not None:
      match = re.search(r'/([^/]+)/?$', url)
      if match is not None:
        region = match.group(1)
        return region
    return 'global'

  @property
  def ssl_certificates(self) -> List[str]:
    return self._resource_data.get('sslCertificates', [])

  @property
  def certificate_map(self) -> str:
    certificate_map = self._resource_data.get('certificateMap', '')
    result = re.match(r'https://certificatemanager.googleapis.com/v1/(.*)',
                      certificate_map)
    if result:
      return result.group(1)
    return certificate_map


@caching.cached_api_call(in_memory=True)
def get_target_https_proxies(project_id: str) -> List[TargetHttpsProxy]:
  logging.debug('fetching Target HTTPS Proxies: %s', project_id)
  compute = apis.get_api('compute', 'v1', project_id)
  target_https_proxies = []
  request = compute.targetHttpsProxies().aggregatedList(project=project_id)
  response = request.execute(num_retries=config.API_RETRIES)
  target_https_proxies_by_region = response['items']
  for _, data_ in target_https_proxies_by_region.items():
    if 'targetHttpsProxies' not in data_:
      continue
    target_https_proxies.extend([
        TargetHttpsProxy(project_id, target_https_proxy)
        for target_https_proxy in data_['targetHttpsProxies']
    ])

  return target_https_proxies


class TargetSslProxy(models.Resource):
  """A Target SSL Proxy resource."""

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
  def self_link(self) -> str:
    return self._resource_data['selfLink']

  @property
  def region(self):
    url = self._resource_data.get('region', '')
    if url is not None:
      match = re.search(r'/([^/]+)/?$', url)
      if match is not None:
        region = match.group(1)
        return region
    return 'global'

  @property
  def ssl_certificates(self) -> List[str]:
    return self._resource_data.get('sslCertificates', [])

  @property
  def certificate_map(self) -> str:
    certificate_map = self._resource_data.get('certificateMap', '')
    result = re.match(r'https://certificatemanager.googleapis.com/v1/(.*)',
                      certificate_map)
    if result:
      return result.group(1)
    return certificate_map


@caching.cached_api_call(in_memory=True)
def get_target_ssl_proxies(project_id: str) -> List[TargetSslProxy]:
  logging.debug('fetching Target SSL Proxies: %s', project_id)
  compute = apis.get_api('compute', 'v1', project_id)
  request = compute.targetSslProxies().list(project=project_id)
  response = request.execute(num_retries=config.API_RETRIES)

  return [
      TargetSslProxy(project_id, item) for item in response.get('items', [])
  ]


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
