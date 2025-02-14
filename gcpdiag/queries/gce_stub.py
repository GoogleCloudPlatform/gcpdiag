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
"""Stub API calls used in gce.py for testing.

Instead of doing real API calls, we return test JSON data.
"""
import json

from gcpdiag.queries import apis_stub, interconnect_stub, lb_stub, network_stub

# pylint: disable=unused-argument
# pylint: disable=invalid-name


class ComputeEngineApiStub(apis_stub.ApiStub):
  """Mock object to simulate compute engine api calls."""

  # mocked methods:
  # gce_api.zones().list(project=project_id).execute()
  # gce_api.zones().list_next(request, response)
  # op1=gce_api.instances().list(project=pid, zone=z)
  # gce_api.new_batch_http_request().add(op1, callback=cb, request_id=id).execute()
  # gce_api.instanceGroupManagers().list(project=project_id, zone=zone)
  # gce_api.regionInstanceGroupManagers().list(project=project_id, region=region)
  # gce_api.instanceGroups().list(project=project_id, zone=zone)
  # gce_api.disks().list(project=project_id, zone=zone)
  # gce_api.instances().get(project=project_id, zone=zone, instance=instance_name)
  # gce_api.instances().getSerialPortOutput(project,zone,instance,start)

  def __init__(self, mock_state='init', project_id=None, zone=None, page=1):
    self.mock_state = mock_state
    self.project_id = project_id
    self.zone = zone
    self.page = page

  def regions(self):
    return ComputeEngineApiStub('regions')

  def zones(self):
    return ComputeEngineApiStub('zones')

  def disks(self):
    return ComputeEngineApiStub('disks')

  def list(self, project, zone=None, returnPartialSuccess=None, fields=None):
    # TODO: implement fields filtering
    if self.mock_state in ['igs', 'instances', 'disks', 'negs']:
      return apis_stub.RestCallStub(
          project,
          f'compute-{self.mock_state}-{zone}',
          default=f'compute-{self.mock_state}-empty',
      )
    elif self.mock_state in ['regions', 'templates', 'zones']:
      return apis_stub.RestCallStub(project, f'compute-{self.mock_state}')
    elif self.mock_state in ['licenses']:
      return apis_stub.RestCallStub(project, f'{project}-licenses')
    else:
      raise RuntimeError(f"can't list for mock state {self.mock_state}")

  def aggregatedList(
      self,
      project,
      filter=None,  # pylint:disable=redefined-builtin
      returnPartialSuccess=None,
      orderBy=None,
      maxResults=None,
      serviceProjectNumber=None,
  ):
    if self.mock_state == 'projects':
      return apis_stub.RestCallStub(project, 'compute-project')
    elif self.mock_state == 'globalOperations':
      return apis_stub.RestCallStub(project, 'global-operations')
    else:
      return apis_stub.RestCallStub(project,
                                    f'compute-{self.mock_state}-aggregated')

  def aggregatedList_next(self, previous_request, previous_response):
    if isinstance(previous_response,
                  dict) and previous_response.get('nextPageToken'):
      return apis_stub.RestCallStub(
          project_id=previous_request.project_id,
          json_basename=previous_request.json_basename,
          page=previous_request.page + 1,
      )
    else:
      return None

  def list_next(self, previous_request, previous_response):
    if isinstance(previous_response,
                  dict) and previous_response.get('nextPageToken'):
      return apis_stub.RestCallStub(
          project_id=previous_request.project_id,
          json_basename=previous_request.json_basename,
          page=previous_request.page + 1,
      )
    else:
      return None

  def instances(self):
    return ComputeEngineApiStub('instances')

  def globalOperations(self):
    return ComputeEngineApiStub('globalOperations')

  def instanceGroupManagers(self):
    return InstanceGroupManagersApiStub()

  def regionInstanceGroupManagers(self):
    return RegionInstanceGroupManagersApiStub()

  def licenses(self):
    return ComputeEngineApiStub('licenses')

  def instanceGroups(self):
    return ComputeEngineApiStub('igs')

  def instanceTemplates(self):
    return ComputeEngineApiStub('templates')

  def getSerialPortOutput(self, project, zone, instance, start):
    return apis_stub.RestCallStub(
        project_id=project,
        json_basename=f'compute-serial-port-output-{instance}',
    )

  def networkEndpointGroups(self):
    return ComputeEngineApiStub('negs')

  def new_batch_http_request(self):
    batch_api = apis_stub.BatchRequestStub()
    if self._fail_count:
      batch_api.fail_next(self._fail_count, self._fail_status)
      self._fail_count = 0
    return batch_api

  def get(self, project, zone=None, instance=None, disk=None):
    if self.mock_state == 'projects':
      return apis_stub.RestCallStub(project, 'compute-project')
    elif self.mock_state == 'instances':
      if instance:
        self.mock_state = 'instance'
        self.instance = instance
        self.project = project
        self.zone = zone
        return self
      else:
        return apis_stub.RestCallStub(project, f'compute-instances-{zone}')
    elif self.mock_state == 'disks':
      if disk:
        self.mock_state = 'disk'
        self.instance = instance
        self.project = project
        self.zone = zone
        self.disk = disk
        return self
      else:
        return apis_stub.RestCallStub(project,
                                      f'compute-instances-disks-{zone}')

  def projects(self):
    return ComputeEngineApiStub('projects')

  def addresses(self):
    return network_stub.NetworkApiStub(mock_state='addresses')

  def networks(self):
    return network_stub.NetworkApiStub(mock_state='networks')

  def subnetworks(self):
    return network_stub.NetworkApiStub(mock_state='subnetworks')

  def routes(self):
    return network_stub.NetworkApiStub(mock_state='routes')

  def routers(self):
    return network_stub.NetworkApiStub(mock_state='routers')

  def backendServices(self):
    return lb_stub.LbApiStub(mock_state='backendServices')

  def regionBackendServices(self):
    return lb_stub.LbApiStub(mock_state='regionBackendServices')

  def targetHttpsProxies(self):
    return lb_stub.TargetProxyStub(mock_state='targetHttpsProxies')

  def targetSslProxies(self):
    return lb_stub.TargetProxyStub(mock_state='targetSslProxies')

  def sslCertificates(self):
    return lb_stub.SslCertificateApiStub(mock_state='sslCertificates')

  def regionSslCertificates(self):
    return lb_stub.SslCertificateApiStub(mock_state='regionSslCertificates')

  def forwardingRules(self):
    return lb_stub.LbApiStub(mock_state='forwardingRules')

  def globalForwardingRules(self):
    return lb_stub.LbApiStub(mock_state='globalForwardingRules')

  def healthChecks(self):
    return HealthCheckApiStub(mock_state='healthChecks')

  def regionHealthChecks(self):
    return HealthCheckApiStub(mock_state='regionHealthChecks')

  def interconnects(self):
    return interconnect_stub.InterconnectApiStub(mock_state='interconnects')

  def interconnectAttachments(self):
    return interconnect_stub.VlanAttachmentApiStub(mock_state='vlan_attachment')

  def execute(self, num_retries=0):
    json_dir = apis_stub.get_json_dir(self.project)
    with open(json_dir / f'compute-instances-{self.zone}.json',
              encoding='utf-8') as json_file:
      instances = json.load(json_file)['items']
      # get instance
      if self.mock_state == 'instance':
        for instance in instances:
          if instance['name'] == self.instance:
            return instance
      # get network interface
      elif self.mock_state == 'effective_firewalls':
        for instance in instances:
          if instance['name'] == self.instance:
            interfaces = instance['networkInterfaces']
            if self.network_interface:
              for interface in interfaces:
                if interface['name'] == self.network_interface:
                  return interface
            else:
              return interfaces
      elif self.mock_state == 'disk':
        with open(
            json_dir / f'compute-instances-disks-{self.zone}.json',
            encoding='utf-8',
        ) as json_file:
          disks = json.load(json_file)['items']
          for disk in disks:
            if disk['name'] == self.disk:
              return disk
      else:
        raise ValueError(
            f"can't call this method here (mock_state: {self.mock_state}")

  def getEffectiveFirewalls(self, project, zone, instance, networkInterface):
    self.mock_state = 'effective_firewalls'
    self.instance = instance
    self.project = project
    self.zone = zone
    self.network_interface = networkInterface
    return self


class InstanceGroupManagersApiStub(ComputeEngineApiStub):
  """Mock object to simulate zonal instance group managers api calls"""

  def list(self, project, zone=None):
    return apis_stub.RestCallStub(project,
                                  f'compute-migs-{zone}',
                                  default='compute-migs-empty')

  def aggregatedList(self, project, returnPartialSuccess=True):
    return apis_stub.RestCallStub(project, 'compute-migs-aggregated')

  def aggregatedList_next(self, previous_request, previous_response):
    if isinstance(previous_response,
                  dict) and previous_response.get('nextPageToken'):
      return apis_stub.RestCallStub(
          project_id=previous_request.project_id,
          json_basename=previous_request.json_basename,
          page=previous_request.page + 1,
      )
    else:
      return None


class RegionInstanceGroupManagersApiStub(ComputeEngineApiStub):
  """Mock object to simulate regional instance group managers api calls"""

  def list(self, project, region=None):
    return apis_stub.RestCallStub(project,
                                  f'compute-migs-{region}',
                                  default='compute-migs-empty')


class HealthCheckApiStub:
  """Mock object to simulate health check api calls"""

  def __init__(self, mock_state):
    self.mock_state = mock_state

  # pylint: disable=redefined-builtin
  def list(self, project, region=None):
    if self.mock_state == 'healthChecks':
      return apis_stub.RestCallStub(project, 'lb-health-checks')
    if self.mock_state == 'regionHealthChecks':
      return apis_stub.RestCallStub(project, f'regionHealthChecks-{region}')
    else:
      raise ValueError(f'cannot call method {self.mock_state} here')

  def get(self, project, healthCheck=None, region=None):
    if healthCheck:
      self.health_check = healthCheck
      self.project = project
      self.region = region
      return self
    else:
      raise ValueError(f'cannot call method {self.mock_state} here')

  def execute(self, num_retries=0):
    json_dir = apis_stub.get_json_dir(self.project)
    json_file_name = f'{self.mock_state}.json'
    if self.mock_state == 'regionHealthChecks':
      json_file_name = f'{self.mock_state}-{self.region}.json'
    with open(json_dir / json_file_name, encoding='utf-8') as json_file:
      health_checks = json.load(json_file)['items']
      # search for and get the health check
      if health_checks:
        for health_check in health_checks:
          if health_check['name'] == self.health_check:
            return health_check
          else:
            raise ValueError(
                f'the health check {self.health_check} is not found')
      else:
        raise ValueError(f'cannot call method {self.mock_state} here')
