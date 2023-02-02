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
"""Queries related to GCP Kubernetes Engine clusters."""

import ipaddress
import logging
import re
from datetime import datetime, timezone
from typing import Dict, Iterable, List, Mapping, Optional, Set

import googleapiclient.errors

from gcpdiag import caching, config, models, utils
from gcpdiag.queries import apis, apis_utils, crm
from gcpdiag.queries import network as network_q


class InstanceTemplate(models.Resource):
  """Represents a GCE Instance Template."""
  _resource_data: dict

  def __init__(self, project_id, resource_data):
    super().__init__(project_id=project_id)
    self._resource_data = resource_data

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

  @property
  def name(self) -> str:
    return self._resource_data['name']

  @property
  def tags(self) -> List[str]:
    return self._resource_data['properties'].get('tags', {}).get('items', [])

  @property
  def service_account(self) -> Optional[str]:
    sa_list = self._resource_data['properties'].get('serviceAccounts', [])
    if not sa_list:
      return None
    email = sa_list[0]['email']
    if email == 'default':
      project_nr = crm.get_project(self._project_id).number
      return f'{project_nr}-compute@developer.gserviceaccount.com'
    return email

  @property
  def network(self) -> network_q.Network:
    return network_q.get_network_from_url(
        self._resource_data['properties']['networkInterfaces'][0]['network'])

  @property
  def subnetwork(self) -> network_q.Subnetwork:
    subnet_url = self._resource_data['properties']['networkInterfaces'][0][
        'subnetwork']
    return self.network.subnetworks[subnet_url]


class InstanceGroup(models.Resource):
  """Represents a GCE instance group."""
  _resource_data: dict

  def __init__(self, project_id, resource_data):
    super().__init__(project_id=project_id)
    self._resource_data = resource_data

  @property
  def full_path(self) -> str:
    result = re.match(r'https://www.googleapis.com/compute/v1/(.*)',
                      self._resource_data['selfLink'])
    if result:
      return result.group(1)
    else:
      return '>> ' + self._resource_data['selfLink']

  @property
  def short_path(self) -> str:
    path = self.project_id + '/' + self.name
    return path

  @property
  def self_link(self) -> str:
    return self._resource_data['selfLink']

  @property
  def name(self) -> str:
    return self._resource_data['name']

  @property
  def named_ports(self) -> List[dict]:
    if 'namedPorts' in self._resource_data:
      return self._resource_data['namedPorts']
    return []

  def has_named_ports(self) -> bool:
    if 'namedPorts' in self._resource_data:
      return True
    return False


class ManagedInstanceGroup(models.Resource):
  """Represents a GCE managed instance group."""
  _resource_data: dict
  _region: Optional[str]

  def __init__(self, project_id, resource_data):
    super().__init__(project_id=project_id)
    self._resource_data = resource_data
    self._region = None

  @property
  def full_path(self) -> str:
    result = re.match(r'https://www.googleapis.com/compute/v1/(.*)',
                      self._resource_data['selfLink'])
    if result:
      return result.group(1)
    else:
      return '>> ' + self._resource_data['selfLink']

  @property
  def short_path(self) -> str:
    path = self.project_id + '/' + self.name
    return path

  def is_gke(self) -> bool:
    """Is this managed instance group part of a GKE cluster?

    Note that the results are based on heuristics (the mig name),
    which is not ideal.
    """

    # gke- is normal GKE, gk3- is GKE autopilot
    return self.name.startswith('gke-') or self.name.startswith('gk3-')

  @property
  def self_link(self) -> str:
    return self._resource_data['selfLink']

  @property
  def name(self) -> str:
    return self._resource_data['name']

  @property
  def region(self) -> str:
    if self._region is None:
      if 'region' in self._resource_data:
        m = re.search(r'/regions/([^/]+)$', self._resource_data['region'])
        if not m:
          raise RuntimeError('can\'t determine region of mig %s (%s)' %
                             (self.name, self._resource_data['region']))
        self._region = m.group(1)
      elif 'zone' in self._resource_data:
        m = re.search(r'/zones/([^/]+)$', self._resource_data['zone'])
        if not m:
          raise RuntimeError('can\'t determine region of mig %s (%s)' %
                             (self.name, self._resource_data['region']))
        zone = m.group(1)
        self._region = utils.zone_region(zone)
      else:
        raise RuntimeError(
            f"can't determine region of mig {self.name}, both region and zone aren't set!"
        )
    return self._region

  def is_instance_member(self, project_id: str, region: str,
                         instance_name: str):
    """Given the project_id, region and instance name, is it a member of this MIG?"""
    return self.project_id == project_id and self.region == region and \
        instance_name.startswith(self._resource_data['baseInstanceName'])

  @property
  def template(self) -> InstanceTemplate:
    if 'instanceTemplate' not in self._resource_data:
      raise RuntimeError('instanceTemplate not set for MIG {self.name}')
    m = re.match(
        r'https://www.googleapis.com/compute/v1/projects/([^/]+)/global/instanceTemplates/([^/]+)',
        self._resource_data['instanceTemplate'])
    if not m:
      raise RuntimeError("can't parse instanceTemplate: %s" %
                         self._resource_data['instanceTemplate'])
    (project_id, template_name) = (m.group(1), m.group(2))
    templates = get_instance_templates(project_id)
    if template_name not in templates:
      raise RuntimeError(
          f'instanceTemplate {template_name} for MIG {self.name} not found')
    return templates[template_name]


class Instance(models.Resource):
  """Represents a GCE instance."""
  _resource_data: dict
  _region: Optional[str]

  def __init__(self, project_id, resource_data):
    super().__init__(project_id=project_id)
    self._resource_data = resource_data
    self._metadata_dict = None
    self._region = None

  @property
  def id(self) -> str:
    return self._resource_data['id']

  @property
  def name(self) -> str:
    return self._resource_data['name']

  @property
  def full_path(self) -> str:
    result = re.match(r'https://www.googleapis.com/compute/v1/(.*)',
                      self._resource_data['selfLink'])
    if result:
      return result.group(1)
    else:
      return '>> ' + self._resource_data['selfLink']

  @property
  def short_path(self) -> str:
    # Note: instance names must be unique per project, so no need to add the zone.
    path = self.project_id + '/' + self.name
    return path

  @property
  def creation_timestamp(self) -> datetime:
    """VM creation time, as a *naive* `datetime` object."""
    return datetime.fromisoformat(
        self._resource_data['creationTimestamp']).astimezone(
            timezone.utc).replace(tzinfo=None)

  @property
  def region(self) -> str:
    if self._region is None:
      if 'zone' in self._resource_data:
        m = re.search(r'/zones/([^/]+)$', self._resource_data['zone'])
        if not m:
          raise RuntimeError('can\'t determine region of instance %s (%s)' %
                             (self.name, self._resource_data['region']))
        zone = m.group(1)
        self._region = utils.zone_region(zone)
      else:
        raise RuntimeError(
            f"can't determine region of instance {self.name}, zone isn't set!")
    return self._region

  @property
  def zone(self) -> str:
    zone_uri = self._resource_data['zone']
    m = re.search(r'/zones/([^/]+)$', zone_uri)
    if m:
      return m.group(1)
    else:
      raise RuntimeError(f"can't determine zone of instance {self.name}")

  @property
  def disks(self) -> List[str]:
    if 'disks' in self._resource_data:
      return self._resource_data['disks']
    return []

  def is_serial_port_logging_enabled(self) -> bool:
    value = self.get_metadata('serial-port-logging-enable')
    return bool(value and value.upper() == 'TRUE')

  def is_gke_node(self) -> bool:
    return 'labels' in self._resource_data and \
           'goog-gke-node' in self._resource_data['labels']

  def is_preemptible_vm(self) -> bool:
    return 'scheduling' in self._resource_data and \
      'preemptible' in self._resource_data['scheduling'] and \
      self._resource_data['scheduling']['preemptible']

  def is_windows_machine(self) -> bool:
    if 'disks' in self._resource_data:
      disks = next(iter(self._resource_data['disks']))
      if 'guestOsFeatures' in disks:
        if 'WINDOWS' in [t['type'] for t in iter(disks['guestOsFeatures'])]:
          return True
    return False

  @property
  def network(self) -> network_q.Network:
    # 'https://www.googleapis.com/compute/v1/projects/gcpdiag-gce1-aaaa/global/networks/default'
    network_string = self._resource_data['networkInterfaces'][0]['network']
    m = re.match(r'^.+/projects/([^/]+)/global/networks/([^/]+)$',
                 network_string)
    if not m:
      raise RuntimeError("can't parse network string: %s" % network_string)
    return network_q.get_network(m.group(1), m.group(2))

  @property
  def network_ips(self) -> List[ipaddress.IPv4Address]:
    return [
        ipaddress.ip_address(nic['networkIP'])
        for nic in self._resource_data['networkInterfaces']
    ]

  @property
  def get_network_interfaces(self):
    return self._resource_data['networkInterfaces']

  def get_network_ip_for_instance_interface(
      self, network: str) -> Optional[ipaddress.IPv4Address]:
    """Get the network ip for a nic given a network name"""
    for nic in self._resource_data['networkInterfaces']:
      if nic.get('network') == network:
        return ipaddress.ip_network(nic.get('networkIP'))
    return None

  def secure_boot_enabled(self) -> bool:
    if 'shieldedInstanceConfig' in self._resource_data:
      return self._resource_data['shieldedInstanceConfig']['enableSecureBoot']
    return False

  @property
  def access_scopes(self) -> List[str]:
    if 'serviceAccounts' in self._resource_data:
      saccts = self._resource_data['serviceAccounts']
      if isinstance(saccts, list) and len(saccts) >= 1:
        return saccts[0].get('scopes', [])
    return []

  @property
  def service_account(self) -> Optional[str]:
    if 'serviceAccounts' in self._resource_data:
      saccts = self._resource_data['serviceAccounts']
      if isinstance(saccts, list) and len(saccts) >= 1:
        return saccts[0]['email']
    return None

  @property
  def tags(self) -> List[str]:
    if 'tags' in self._resource_data:
      if 'items' in self._resource_data['tags']:
        return self._resource_data['tags']['items']
    return []

  def get_metadata(self, key: str) -> str:
    if not self._metadata_dict:
      self._metadata_dict = {}
      if 'metadata' in self._resource_data and 'items' in self._resource_data[
          'metadata']:
        for item in self._resource_data['metadata']['items']:
          if 'key' in item and 'value' in item:
            self._metadata_dict[item['key']] = item['value']
    project_metadata = get_project_metadata(self.project_id)
    return self._metadata_dict.get(key, project_metadata.get(key))

  @property  # type: ignore
  @caching.cached_api_call(in_memory=True)
  def mig(self) -> ManagedInstanceGroup:
    """Return ManagedInstanceGroup that owns this instance.

    Throws AttributeError in case it isn't MIG-managed."""

    created_by = self.get_metadata('created-by')
    if created_by is None:
      raise AttributeError(f'instance {self.id} is not managed by a mig')

    # Example created-by:
    # pylint: disable=line-too-long
    # "projects/12340002/zones/europe-west4-a/instanceGroupManagers/gke-gke1-default-pool-e5e20a34-grp"
    # (note how it uses a project number and not a project id...)
    created_by_match = re.match(
        r'projects/([^/]+)/((?:regions|zones)/[^/]+/instanceGroupManagers/[^/]+)$',
        created_by)
    if not created_by_match:
      raise AttributeError(
          f'instance {self.id} is not managed by a mig (created-by={created_by})'
      )
    project = crm.get_project(created_by_match.group(1))

    mig_self_link = ('https://www.googleapis.com/compute/v1/'
                     f'projects/{project.id}/{created_by_match.group(2)}')

    # Try to find a matching mig.
    for mig in get_managed_instance_groups(
        models.Context(project_id=self.project_id)).values():
      if mig.self_link == mig_self_link:
        return mig

    raise AttributeError(f'instance {self.id} is not managed by a mig')


class Disk(models.Resource):
  """Represents a GCE disk."""
  _resource_data: dict

  def __init__(self, project_id, resource_data):
    super().__init__(project_id=project_id)
    self._resource_data = resource_data

  @property
  def id(self) -> str:
    return self._resource_data['id']

  @property
  def name(self) -> str:
    return self._resource_data['name']

  @property
  def zone(self) -> str:
    m = re.search(r'/zones/([^/]+)$', self._resource_data['zone'])
    if not m:
      raise RuntimeError('can\'t determine zone of disk %s (%s)' %
                         (self.name, self._resource_data['zone']))
    return m.group(1)

  @property
  def full_path(self) -> str:
    result = re.match(r'https://www.googleapis.com/compute/v1/(.*)',
                      self._resource_data['selfLink'])
    if result:
      return result.group(1)
    else:
      return '>> ' + self._resource_data['selfLink']

  @property
  def short_path(self) -> str:
    return f'{self.project_id}/{self.name}'

  @property
  def bootable(self) -> bool:
    return 'guestOsFeatures' in self._resource_data

  @property
  def in_use(self) -> bool:
    return 'users' in self._resource_data


@caching.cached_api_call(in_memory=True)
def get_gce_zones(project_id: str) -> Set[str]:
  try:
    gce_api = apis.get_api('compute', 'v1', project_id)
    logging.info('listing gce zones of project %s', project_id)
    request = gce_api.zones().list(project=project_id)
    response = request.execute(num_retries=config.API_RETRIES)
    if not response or 'items' not in response:
      return set()
    return {item['name'] for item in response['items'] if 'name' in item}
  except googleapiclient.errors.HttpError as err:
    raise utils.GcpApiError(err) from err


@caching.cached_api_call(in_memory=True)
def get_instance(project_id: str, zone: str, instance_name: str) -> Instance:
  """Returns instance object matching instance name and zone"""
  compute = apis.get_api('compute', 'v1', project_id)
  request = compute.instances().get(project=project_id,
                                    zone=zone,
                                    instance=instance_name)
  response = request.execute(num_retries=config.API_RETRIES)
  return Instance(project_id, resource_data=response)


@caching.cached_api_call(in_memory=True)
def get_instances(context: models.Context) -> Mapping[str, Instance]:
  """Get a list of Instance matching the given context, indexed by instance id."""

  instances: Dict[str, Instance] = {}
  if not apis.is_enabled(context.project_id, 'compute'):
    return instances
  gce_api = apis.get_api('compute', 'v1', context.project_id)
  requests = [
      gce_api.instances().list(project=context.project_id, zone=zone)
      for zone in get_gce_zones(context.project_id)
  ]
  items = apis_utils.batch_list_all(
      api=gce_api,
      requests=requests,
      next_function=gce_api.instances().list_next,
      log_text=f'listing gce instances of project {context.project_id}')
  for i in items:
    result = re.match(
        r'https://www.googleapis.com/compute/v1/projects/[^/]+/zones/([^/]+)/',
        i['selfLink'])
    if not result:
      logging.error('instance %s selfLink didn\'t match regexp: %s', i['id'],
                    i['selfLink'])
      continue
    zone = result.group(1)
    labels = i.get('labels', {})
    if not context.match_project_resource(location=zone, labels=labels):
      continue
    instances[i['id']] = Instance(project_id=context.project_id,
                                  resource_data=i)
  return instances


@caching.cached_api_call(in_memory=True)
def get_instance_groups(context: models.Context) -> Mapping[str, InstanceGroup]:
  """Get a list of InstanceGroups matching the given context, indexed by name."""
  groups: Dict[str, InstanceGroup] = {}
  if not apis.is_enabled(context.project_id, 'compute'):
    return groups
  gce_api = apis.get_api('compute', 'v1', context.project_id)
  requests = [
      gce_api.instanceGroups().list(project=context.project_id, zone=zone)
      for zone in get_gce_zones(context.project_id)
  ]
  items = apis_utils.batch_list_all(
      api=gce_api,
      requests=requests,
      next_function=gce_api.instanceGroups().list_next,
      log_text=f'listing gce instances of project {context.project_id}')
  for i in items:
    groups[i['name']] = InstanceGroup(context.project_id, i)
  return groups


@caching.cached_api_call(in_memory=True)
def get_managed_instance_groups(
    context: models.Context) -> Mapping[int, ManagedInstanceGroup]:
  """Get a list of ManagedInstanceGroups matching the given context, indexed by mig id."""

  migs: Dict[int, ManagedInstanceGroup] = {}
  if not apis.is_enabled(context.project_id, 'compute'):
    return migs
  gce_api = apis.get_api('compute', 'v1', context.project_id)
  requests = [
      gce_api.instanceGroupManagers().list(project=context.project_id,
                                           zone=zone)
      for zone in get_gce_zones(context.project_id)
  ]
  items = apis_utils.batch_list_all(
      api=gce_api,
      requests=requests,
      next_function=gce_api.instanceGroupManagers().list_next,
      log_text=f'listing managed instance groups of project {context.project_id}'
  )
  for i in items:
    result = re.match(
        r'https://www.googleapis.com/compute/v1/projects/[^/]+/(?:regions|zones)/([^/]+)/',
        i['selfLink'])
    if not result:
      logging.error('mig %s selfLink didn\'t match regexp: %s', i['name'],
                    i['selfLink'])
      continue
    location = result.group(1)
    labels = i.get('labels', {})
    if not context.match_project_resource(location=location, labels=labels):
      continue
    migs[i['id']] = ManagedInstanceGroup(project_id=context.project_id,
                                         resource_data=i)
  return migs


@caching.cached_api_call
def get_instance_templates(project_id: str) -> Mapping[str, InstanceTemplate]:
  logging.info('fetching instance templates')
  templates = {}
  gce_api = apis.get_api('compute', 'v1', project_id)
  request = gce_api.instanceTemplates().list(
      project=project_id,
      returnPartialSuccess=True,
      # Fetch only a subset of the fields to improve performance.
      fields=
      ('items/name, items/properties/tags, items/properties/networkInterfaces, '
       'items/properties/serviceAccounts'),
  )
  for t in apis_utils.list_all(
      request, next_function=gce_api.instanceTemplates().list_next):
    templates[t['name']] = InstanceTemplate(project_id, t)
  return templates


@caching.cached_api_call
def get_project_metadata(project_id) -> Mapping[str, str]:
  gce_api = apis.get_api('compute', 'v1', project_id)
  logging.info('fetching metadata of project %s', project_id)
  query = gce_api.projects().get(project=project_id)
  try:
    response = query.execute(num_retries=config.API_RETRIES)
  except googleapiclient.errors.HttpError as err:
    raise utils.GcpApiError(err) from err

  mapped_metadata: Dict[str, str] = {}
  metadata = response.get('commonInstanceMetadata')
  if metadata and 'items' in metadata:
    for m_item in metadata['items']:
      mapped_metadata[m_item.get('key')] = m_item.get('value')
  return mapped_metadata


class Region(models.Resource):
  """Represents a GCE Region."""
  _resource_data: dict

  def __init__(self, project_id, resource_data):
    super().__init__(project_id=project_id)
    self._resource_data = resource_data

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
  def name(self) -> str:
    return self._resource_data['name']


@caching.cached_api_call
def get_all_regions(project_id: str) -> Iterable[Region]:
  """Return list of all regions

  Args:
      project_id (str): project id for this request

  Raises:
      utils.GcpApiError: Raises GcpApiError in case of query issues

  Returns:
      Iterable[Region]: Return list of all regions
  """
  try:
    gce_api = apis.get_api('compute', 'v1', project_id)
    request = gce_api.regions().list(project=project_id)
    response = request.execute(num_retries=config.API_RETRIES)
    if not response or 'items' not in response:
      return set()

    return {
        Region(project_id, item) for item in response['items'] if 'name' in item
    }
  except googleapiclient.errors.HttpError as err:
    raise utils.GcpApiError(err) from err


def get_regions_with_instances(context: models.Context) -> Iterable[Region]:
  """Return list of regions with instances

  Args:
      context (models.Context): context for this request

  Returns:
      Iterable[Region]: Return list of regions which contains instances
  """

  regions_of_instances = {i.region for i in get_instances(context).values()}

  all_regions = get_all_regions(context.project_id)
  if not all_regions:
    return set()

  return {r for r in all_regions if r.name in regions_of_instances}


@caching.cached_api_call
def get_all_disks(project_id: str) -> Iterable[Disk]:
  try:
    gce_api = apis.get_api('compute', 'v1', project_id)
    requests = [
        gce_api.disks().list(project=project_id, zone=zone)
        for zone in get_gce_zones(project_id)
    ]
    items = apis_utils.batch_list_all(
        api=gce_api,
        requests=requests,
        next_function=gce_api.disks().list_next,
        log_text=f'listing gce disks of project {project_id}')

    return {Disk(project_id, item) for item in items}

  except googleapiclient.errors.HttpError as err:
    raise utils.GcpApiError(err) from err


class InstanceEffectiveFirewalls(network_q.EffectiveFirewalls):
  """Effective firewall rules for a network interace on a VM instance.

  Includes org/folder firewall policies)."""
  _instance: Instance
  _nic: str

  def __init__(self, instance, nic, resource_data):
    super().__init__(resource_data)
    self._instance = instance
    self._nic = nic


@caching.cached_api_call(in_memory=True)
def get_instance_interface_effective_firewalls(
    instance: Instance, nic: str) -> InstanceEffectiveFirewalls:
  """Return effective firewalls for a network interface on the instance"""
  compute = apis.get_api('compute', 'v1', instance.project_id)
  request = compute.instances().getEffectiveFirewalls(
      project=instance.project_id,
      zone=instance.zone,
      instance=instance.name,
      networkInterface=nic)
  response = request.execute(num_retries=config.API_RETRIES)
  return InstanceEffectiveFirewalls(Instance, nic, response)
