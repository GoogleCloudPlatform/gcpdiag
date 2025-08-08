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
"""Stub API calls used in lb.py for testing.

Instead of doing real API calls, we return test JSON data.
"""

import json
from typing import Any

import httplib2
from googleapiclient import errors

from gcpdiag.queries import apis_stub

# pylint: disable=unused-argument
# pylint: disable=invalid-name

backend_service_states = ('backendServices', 'regionBackendServices')
forwarding_rule_states = ('forwardingRules', 'globalForwardingRules')
target_http_proxy_states = ('targetHttpProxies', 'regionTargetHttpProxies')
target_https_proxy_states = (
    'targetHttpsProxies',
    'regionTargetHttpsProxies',
)
target_ssl_proxy_states = 'targetSslProxies'
target_grpc_proxy_states = 'targetGrpcProxies'
target_tcp_proxy_states = ('targetTcpProxies', 'regionTargetTcpProxies')

aggregated_supported = (
    'backendServices',
    'forwardingRules',
    'targetHttpProxies',
    'targetHttpsProxies',
    'targetTcpProxies',
)


class LbApiStub:
  """Mock object to simulate compute engine networking api calls.

  This object is created by GceApiStub, not used directly in test scripts.
  """

  def __init__(self, mock_state):
    self.mock_state = mock_state

  def aggregatedList(self, project):
    if self.mock_state == 'forwardingRules':
      return apis_stub.RestCallStub(project,
                                    'compute-aggregated-forwardingRules')
    if self.mock_state == 'backendServices':
      return apis_stub.RestCallStub(project,
                                    'compute-aggregated-backendServices')
    else:
      raise ValueError(f'cannot call method {self.mock_state} here')

  # pylint: disable=redefined-builtin
  def list(self, project, region=None):
    if self.mock_state == 'backendServices':
      return apis_stub.RestCallStub(project, 'compute-backendServices')
    if self.mock_state == 'regionBackendServices':
      return apis_stub.RestCallStub(project,
                                    f'compute-backendServices-{region}')
    else:
      raise ValueError(f'cannot call method {self.mock_state} here')

  def get(
      self,
      project,
      region=None,
      backendService=None,
      forwardingRule=None,
  ):
    self.region = region
    self.project = project
    if self.mock_state in backend_service_states and backendService:
      self.backend_service = backendService
      return self
    elif self.mock_state in forwarding_rule_states and forwardingRule:
      self.forwarding_rule = forwardingRule
      return self
    else:
      raise ValueError(f'cannot call method {self.mock_state} here')

  def getHealth(self, project, backendService, body, region=None):
    backend_url_parts = body.get('group').split('/')
    backend_name, backend_type, backend_scope = (
        backend_url_parts[-1],
        backend_url_parts[-2],
        backend_url_parts[-3],
    )

    if self.mock_state == 'backendServices':
      stub_name = (f'backendService-{backendService}-get-health-{backend_type}-'
                   f'{backend_name}-{backend_scope}')
      return apis_stub.RestCallStub(project, stub_name)
    if self.mock_state == 'regionBackendServices':
      stub_name = (f'regionBackendService-{backendService}-{region}-get-health-'
                   f'{backend_type}-{backend_name}-{backend_scope}')
      return apis_stub.RestCallStub(project, stub_name)
    else:
      raise ValueError(f'cannot call method {self.mock_state} here')

  def _get_resources_from_json_items(self, items: Any, resource_name: str):
    if resource_name in aggregated_supported:
      items_by_scope = items[f'regions/{self.region}' if self.
                             region else 'global']
      return items_by_scope[resource_name]
    return items

  def execute(self, num_retries=0):
    json_dir = apis_stub.get_json_dir(self.project)
    if self.mock_state in backend_service_states:
      resource_name = 'backendServices'
    elif self.mock_state in forwarding_rule_states:
      resource_name = 'forwardingRules'
    else:
      resource_name = self.mock_state
    json_file_name = (f'compute-aggregated-{resource_name}.json'
                      if resource_name in aggregated_supported else
                      f'compute-{resource_name}.json')

    with open(json_dir / f'{json_file_name}', encoding='utf-8') as json_file:
      items = json.load(json_file)['items']
      resources = self._get_resources_from_json_items(items, resource_name)

      if not resources:
        raise errors.HttpError(
            httplib2.Response({
                'status': 404,
                'reason': 'Not Found'
            }),
            b'The resource is not found',
        )
      if self.mock_state in backend_service_states:
        for backend_service in resources:
          if backend_service['name'] == self.backend_service:
            return backend_service
          else:
            raise errors.HttpError(
                httplib2.Response({
                    'status': 404,
                    'reason': 'Not Found'
                }),
                f'The backend service {self.backend_service} is not found'.
                encode(),
            )
      elif self.mock_state in forwarding_rule_states:
        for forwarding_rule in resources:
          if forwarding_rule['name'] == self.forwarding_rule:
            return forwarding_rule
          else:
            raise errors.HttpError(
                httplib2.Response({
                    'status': 404,
                    'reason': 'Not Found'
                }),
                f'The forwarding rule {self.forwarding_rule} is not found'.
                encode(),
            )
      else:
        raise ValueError(f'cannot call method {self.mock_state} here')

  def list_next(self, prev_request, prev_response):
    return None


class SslCertificateApiStub:
  """Mock object to simulate SSL certificate api calls"""

  def __init__(self, mock_state):
    self.mock_state = mock_state

  def get(self, project, sslCertificate=None, region=None):
    if sslCertificate:
      self.ssl_certificate = sslCertificate
      self.project = project
      self.region = region
      return self
    else:
      raise ValueError(f'cannot call method {self.mock_state} here')

  def execute(self, num_retries=0):
    json_dir = apis_stub.get_json_dir(self.project)
    json_file_name = f'compute-{self.mock_state}.json'
    if self.mock_state == 'regionSslCertificates':
      json_file_name = f'compute-{self.mock_state}-{self.region}.json'
    with open(json_dir / json_file_name, encoding='utf-8') as json_file:
      ssl_certificates = json.load(json_file)['items']
      # search for and get the ssl certificate
      if ssl_certificates:
        for ssl_certificate in ssl_certificates:
          if ssl_certificate['name'] == self.ssl_certificate:
            return ssl_certificate
        raise errors.HttpError(
            httplib2.Response({
                'status': 404,
                'reason': 'Not Found'
            }),
            f'The SSL certificate {self.ssl_certificate} is not found'.encode(),
        )
      else:
        raise ValueError(f'cannot call method {self.mock_state} here')


class TargetProxyStub:
  """Mock object to simulate target proxy api calls"""

  def __init__(self, mock_state):
    self.mock_state = mock_state

  def aggregatedList(self, project):
    return apis_stub.RestCallStub(project,
                                  f'compute-aggregated-{self.mock_state}')

  def list(self, project):
    return apis_stub.RestCallStub(project, f'compute-{self.mock_state}')

  def get(
      self,
      project,
      region=None,
      targetHttpProxy=None,
      targetHttpsProxy=None,
      targetSslProxy=None,
      targetGrpcProxy=None,
      targetTcpProxy=None,
  ):
    self.region = region
    self.project = project
    if self.mock_state in target_tcp_proxy_states and targetTcpProxy:
      self.target_proxy = targetTcpProxy
      return self
    if self.mock_state in target_https_proxy_states and targetHttpsProxy:
      self.target_proxy = targetHttpsProxy
      return self
    if self.mock_state in target_http_proxy_states and targetHttpProxy:
      self.target_proxy = targetHttpProxy
      return self
    if self.mock_state in target_ssl_proxy_states and targetSslProxy:
      self.target_proxy = targetSslProxy
      return self
    if self.mock_state in target_grpc_proxy_states and targetGrpcProxy:
      self.target_proxy = targetGrpcProxy
      return self
    else:
      raise ValueError(f'cannot call method {self.mock_state} here')

  def execute(self, num_retries=0):
    json_dir = apis_stub.get_json_dir(self.project)
    json_file_name = f'compute-{self.mock_state}.json'
    if self.region:
      json_file_name = f'compute-{self.mock_state}-{self.region}.json'
    with open(json_dir / json_file_name, encoding='utf-8') as json_file:
      target_proxies = json.load(json_file)['items']
      # search for and get the ssl certificate
      if target_proxies:
        for target_proxy in target_proxies:
          if target_proxy['name'] == self.target_proxy:
            return target_proxy
        raise errors.HttpError(
            httplib2.Response({
                'status': 404,
                'reason': 'Not Found'
            }),
            f'The Target proxy {self.target_proxy} is not found'.encode(),
        )
      else:
        raise ValueError(f'cannot call method {self.mock_state} here')
