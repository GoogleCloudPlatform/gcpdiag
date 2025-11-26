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
"""Queries related to GCP Compute Engine."""

import concurrent.futures
import dataclasses
import ipaddress
import logging
import re
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Set

import googleapiclient.errors
from boltons.iterutils import get_path

from gcpdiag import caching, config, executor, models, utils
from gcpdiag.queries import apis, apis_utils, crm
from gcpdiag.queries import network as network_q

POSITIVE_BOOL_VALUES = {'Y', 'YES', 'TRUE', '1'}

DATAPROC_LABEL = 'goog-dataproc-cluster-name'
GKE_LABEL = 'goog-gke-node'


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

  def get_metadata(self, key: str) -> str:
    for item in self._resource_data['properties']['metadata']['items']:
      if item['key'] == key:
        return item['value']
    return ''


class InstanceGroup(models.Resource):
  """Represents a GCE instance group."""

  _resource_data: dict

  def __init__(self, project_id, resource_data):
    super().__init__(project_id=project_id)
    self._resource_data = resource_data

  @property
  def full_path(self) -> str:
    result = re.match(
        r'https://www.googleapis.com/compute/v1/(.*)',
        self._resource_data['selfLink'],
    )
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
    result = re.match(
        r'https://www.googleapis.com/compute/v1/(.*)',
        self._resource_data['selfLink'],
    )
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

    Returns:
        bool: True if this managed instance group is part of a GKE cluster.
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
          raise RuntimeError("can't determine region of mig %s (%s)" %
                             (self.name, self._resource_data['region']))
        self._region = m.group(1)
      elif 'zone' in self._resource_data:
        m = re.search(r'/zones/([^/]+)$', self._resource_data['zone'])
        if not m:
          raise RuntimeError("can't determine region of mig %s (%s)" %
                             (self.name, self._resource_data['region']))
        zone = m.group(1)
        self._region = utils.zone_region(zone)
      else:
        raise RuntimeError(
            f"can't determine region of mig {self.name}, both region and zone"
            " aren't set!")
    return self._region

  @property
  def zone(self) -> Optional[str]:
    if 'zone' in self._resource_data:
      m = re.search(r'/zones/([^/]+)$', self._resource_data['zone'])
      if not m:
        raise RuntimeError("can't determine zone of mig %s (%s)" %
                           (self.name, self._resource_data['zone']))
      return m.group(1)
    return None

  def count_no_action_instances(self) -> int:
    """number of instances in the mig that are running and have no scheduled actions."""
    return self._resource_data['currentActions']['none']

  def is_instance_member(self, project_id: str, region: str,
                         instance_name: str):
    """Given the project_id, region and instance name, is it a member of this MIG?"""
    return (self.project_id == project_id and self.region == region and
            instance_name.startswith(self._resource_data['baseInstanceName']))

  @property
  def template(self) -> InstanceTemplate:
    if 'instanceTemplate' not in self._resource_data:
      raise RuntimeError('instanceTemplate not set for MIG {self.name}')

    m = re.match(
        r'https://www.googleapis.com/compute/v1/(.*)',
        self._resource_data['instanceTemplate'],
    )

    if not m:
      raise RuntimeError("can't parse instanceTemplate: %s" %
                         self._resource_data['instanceTemplate'])
    template_self_link = m.group(1)
    templates = get_instance_templates(self.project_id)
    if template_self_link not in templates:
      raise RuntimeError(
          f'instanceTemplate {template_self_link} for MIG {self.name} not found'
      )
    return templates[template_self_link]

  @property
  def version_target_reached(self) -> bool:
    return get_path(self._resource_data,
                    ('status', 'versionTarget', 'isReached'))

  def get(self, path: str, default: Any = None) -> Any:
    """Gets a value from resource_data using a dot-separated path."""
    return get_path(self._resource_data,
                    tuple(path.split('.')),
                    default=default)


class Autoscaler(models.Resource):
  """Represents a GCE Autoscaler."""

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

  def get(self, path: str, default: Any = None) -> Any:
    """Gets a value from resource_data using a dot-separated path."""
    return get_path(self._resource_data,
                    tuple(path.split('.')),
                    default=default)


class SerialPortOutput:
  """Represents the full Serial Port Output (/dev/ttyS0 or COM1) of an instance.

  contents is the full 1MB of the instance.
  """

  _project_id: str
  _instance_id: str
  _contents: List[str]

  def __init__(self, project_id, instance_id, contents):
    self._project_id = project_id
    self._instance_id = instance_id
    self._contents = contents

  @property
  def contents(self) -> List[str]:
    return self._contents

  @property
  def instance_id(self) -> str:
    return self._instance_id


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
    result = re.match(
        r'https://www.googleapis.com/compute/v1/(.*)',
        self._resource_data['selfLink'],
    )
    if result:
      return result.group(1)
    else:
      return '>> ' + self._resource_data['selfLink']

  @property
  def short_path(self) -> str:
    # Note: instance names must be unique per project,
    # so no need to add the zone.
    path = self.project_id + '/' + self.name
    return path

  @property
  def creation_timestamp(self) -> datetime:
    """VM creation time, as a *naive* `datetime` object."""
    return (datetime.fromisoformat(
        self._resource_data['creationTimestamp']).astimezone(
            timezone.utc).replace(tzinfo=None))

  @property
  def region(self) -> str:
    if self._region is None:
      if 'zone' in self._resource_data:
        m = re.search(r'/zones/([^/]+)$', self._resource_data['zone'])
        if not m:
          raise RuntimeError("can't determine region of instance %s (%s)" %
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
  def disks(self) -> List[dict]:
    if 'disks' in self._resource_data:
      return self._resource_data['disks']
    return []

  @property
  def boot_disk_licenses(self) -> List[str]:
    """Returns license names associated with boot disk."""
    for disk in self.disks:
      if disk.get('boot'):
        return [
            l.partition('/global/licenses/')[2]
            for l in disk.get('licenses', [])
        ]
    return []

  @property
  def guest_os_features(self) -> List[str]:
    """Returns guestOsFeatures types associated with boot disk."""
    for disk in self.disks:
      if disk.get('boot'):
        return [f['type'] for f in disk.get('guestOsFeatures', [])]
    return []

  @property
  def startrestricted(self) -> bool:
    return self._resource_data['startRestricted']

  def laststarttimestamp(self) -> str:
    return self._resource_data['lastStartTimestamp']

  def laststoptimestamp(self) -> str:
    if 'lastStopTimestamp' in self._resource_data:
      return self._resource_data['lastStopTimestamp']
    return ''

  def is_serial_port_logging_enabled(self) -> bool:
    value = self.get_metadata('serial-port-logging-enable')
    return bool(value and value.upper() in POSITIVE_BOOL_VALUES)

  def is_oslogin_enabled(self) -> bool:
    value = self.get_metadata('enable-oslogin')
    return bool(value and value.upper() in POSITIVE_BOOL_VALUES)

  def is_metadata_enabled(self, metadata_name) -> bool:
    """Use to check for common boolean metadata value"""
    value = self.get_metadata(metadata_name)
    return bool(value and value.upper() in POSITIVE_BOOL_VALUES)

  def has_label(self, label) -> bool:
    return label in self.labels

  def is_dataproc_instance(self) -> bool:
    return self.has_label(DATAPROC_LABEL)

  def is_gke_node(self) -> bool:
    return self.has_label(GKE_LABEL)

  @property
  def is_preemptible_vm(self) -> bool:
    return ('scheduling' in self._resource_data and
            'preemptible' in self._resource_data['scheduling'] and
            self._resource_data['scheduling']['preemptible'])

  def min_cpu_platform(self) -> str:
    if 'minCpuPlatform' in self._resource_data:
      return self._resource_data['minCpuPlatform']
    return 'None'

  @property
  def created_by_mig(self) -> bool:
    """Return bool indicating if the instance part of a mig.

    MIG which were part of MIG however have been removed or terminated will
    return True.
    """
    created_by = self.get_metadata('created-by')
    if created_by is None:
      return False

    created_by_match = re.match(
        r'projects/([^/]+)/((?:regions|zones)/[^/]+/instanceGroupManagers/[^/]+)$',
        created_by,
    )
    if not created_by_match:
      return False
    return True

  def is_windows_machine(self) -> bool:
    if 'disks' in self._resource_data:
      disks = next(iter(self._resource_data['disks']))
      if 'guestOsFeatures' in disks:
        if 'WINDOWS' in [t['type'] for t in iter(disks['guestOsFeatures'])]:
          return True
    return False

  def is_public_machine(self) -> bool:
    if 'networkInterfaces' in self._resource_data:
      return 'natIP' in str(self._resource_data['networkInterfaces'])
    return False

  def machine_type(self):
    if 'machineType' in self._resource_data:
      # return self._resource_data['machineType']
      machine_type_uri = self._resource_data['machineType']
      mt = re.search(r'/machineTypes/([^/]+)$', machine_type_uri)
      if mt:
        return mt.group(1)
      else:
        raise RuntimeError(
            f"can't determine machineType of instance {self.name}")
    return None

  def check_license(self, licenses: List[str]) -> bool:
    """Checks that a license is contained in a given license list."""
    if 'disks' in self._resource_data:
      for disk in self._resource_data['disks']:
        if 'license' in str(disk):
          for license_ in licenses:
            for attached_license in disk['licenses']:
              if license_ == attached_license.partition('/global/licenses/')[2]:
                return True
    return False

  def get_boot_disk_image(self) -> str:
    """Get VM's boot disk image."""
    boot_disk_image: str = ''
    for disk in self.disks:
      if disk.get('boot', False):
        disk_source = disk.get('source', '')
        m = re.search(r'/disks/([^/]+)$', disk_source)
        if not m:
          raise RuntimeError(f"can't determine name of boot disk {disk_source}")
        disk_name = m.group(1)
        gce_disk: Disk = get_disk(self.project_id,
                                  zone=self.zone,
                                  disk_name=disk_name)
        return gce_disk.source_image
    return boot_disk_image

  @property
  def is_sole_tenant_vm(self) -> bool:
    return bool('nodeAffinities' in self._resource_data['scheduling'])

  @property
  def network(self) -> network_q.Network:
    # 'https://www.googleapis.com/compute/v1/projects/gcpdiag-gce1-aaaa/global/networks/default'
    network_string = self._resource_data['networkInterfaces'][0]['network']
    m = re.match(r'^.+/projects/([^/]+)/global/networks/([^/]+)$',
                 network_string)
    if not m:
      raise RuntimeError("can't parse network string: %s" % network_string)
    return network_q.get_network(m.group(1),
                                 m.group(2),
                                 context=models.Context(project_id=m.group(1)))

  @property
  def network_ips(self) -> List[network_q.IPv4AddrOrIPv6Addr]:
    return [
        ipaddress.ip_address(nic['networkIP'])
        for nic in self._resource_data['networkInterfaces']
    ]

  @property
  def get_network_interfaces(self):
    return self._resource_data['networkInterfaces']

  @property
  def subnetworks(self) -> List[network_q.Subnetwork]:
    subnetworks = []
    for nic in self._resource_data['networkInterfaces']:
      subnetworks.append(network_q.get_subnetwork_from_url(nic['subnetwork']))
    return subnetworks

  @property
  def routes(self) -> List[network_q.Route]:
    routes = []
    for nic in self._resource_data['networkInterfaces']:
      for route in network_q.get_routes(self.project_id):
        if nic['network'] == route.network:
          if route.tags == []:
            routes.append(route)
            continue
          else:
            temp = [x for x in self.tags if x in route.tags]
            if len(temp) > 0:
              routes.append(route)
    return routes

  def get_network_ip_for_instance_interface(
      self, network: str) -> Optional[network_q.IPv4NetOrIPv6Net]:
    """Get the network ip for a nic given a network name."""
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
      if ('metadata' in self._resource_data and
          'items' in self._resource_data['metadata']):
        for item in self._resource_data['metadata']['items']:
          if 'key' in item and 'value' in item:
            self._metadata_dict[item['key']] = item['value']
    project_metadata = get_project_metadata(self.project_id)
    return self._metadata_dict.get(key, project_metadata.get(key))

  @property
  def status(self) -> str:
    """VM Status."""
    return self._resource_data.get('status', None)

  @property
  def is_running(self) -> bool:
    """VM Status is indicated as running."""
    return self._resource_data.get('status', False) == 'RUNNING'

  @property
  def network_interface_count(self) -> int:
    """Returns the number of network interfaces attached to the instance."""
    return len(self._resource_data.get('networkInterfaces', []))

  @property  # type: ignore
  @caching.cached_api_call(in_memory=True)
  def mig(self) -> ManagedInstanceGroup:
    """Return ManagedInstanceGroup that owns this instance.

    Throws AttributeError in case it isn't MIG-managed.
    """

    created_by = self.get_metadata('created-by')
    if created_by is None:
      raise AttributeError(f'instance {self.id} is not managed by a mig')

    # Example created-by:
    # pylint: disable=line-too-long
    # "projects/12340002/zones/europe-west4-a/instanceGroupManagers/gke-gke1-default-pool-e5e20a34-grp"
    # (note how it uses a project number and not a project id...)
    created_by_match = re.match(
        r'projects/([^/]+)/((?:regions|zones)/[^/]+/instanceGroupManagers/[^/]+)$',
        created_by,
    )
    if not created_by_match:
      raise AttributeError(f'instance {self.id} is not managed by a mig'
                           f' (created-by={created_by})')
    project = crm.get_project(created_by_match.group(1))

    mig_self_link = ('https://www.googleapis.com/compute/v1/'
                     f'projects/{project.id}/{created_by_match.group(2)}')

    # Try to find a matching mig.
    context = models.Context(project_id=self.project_id)
    all_migs = list(get_managed_instance_groups(context).values()) + list(
        get_region_managed_instance_groups(context).values())

    for mig in all_migs:
      if mig.self_link == mig_self_link:
        return mig

    raise AttributeError(f'MIG not found for instance {self.id}. '
                         f'Created by: {created_by}')

  @property
  def labels(self) -> dict:
    return self._resource_data.get('labels', {})


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
  def type(self) -> str:
    disk_type = re.search(r'/diskTypes/([^/]+)$', self._resource_data['type'])
    if not disk_type:
      raise RuntimeError("can't determine type of the disk %s (%s)" %
                         (self.name, self._resource_data['type']))
    return disk_type.group(1)

  @property
  def users(self) -> list:
    pattern = r'/instances/(.+)$'
    # Extracting the instances
    instances = []
    for i in self._resource_data.get('users', []):
      m = re.search(pattern, i)
      if m:
        instances.append(m.group(1))
    return instances

  @property
  def zone(self) -> str:
    m = re.search(r'/zones/([^/]+)$', self._resource_data['zone'])
    if not m:
      raise RuntimeError("can't determine zone of disk %s (%s)" %
                         (self.name, self._resource_data['zone']))
    return m.group(1)

  @property
  def source_image(self) -> str:
    return self._resource_data.get('sourceImage', '')

  @property
  def full_path(self) -> str:
    result = re.match(
        r'https://www.googleapis.com/compute/v1/(.*)',
        self._resource_data['selfLink'],
    )
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

  @property
  def size(self) -> int:
    return self._resource_data['sizeGb']

  @property
  def provisionediops(self) -> Optional[int]:
    return self._resource_data.get('provisionedIops')

  @property
  def has_snapshot_schedule(self) -> bool:
    return 'resourcePolicies' in self._resource_data


@caching.cached_api_call(in_memory=True)
def get_gce_zones(project_id: str) -> Set[str]:
  try:
    gce_api = apis.get_api('compute', 'v1', project_id)
    logging.debug('listing gce zones of project %s', project_id)
    request = gce_api.zones().list(project=project_id)
    response = request.execute(num_retries=config.API_RETRIES)
    if not response or 'items' not in response:
      return set()
    return {item['name'] for item in response['items'] if 'name' in item}
  except googleapiclient.errors.HttpError as err:
    raise utils.GcpApiError(err) from err


def get_gce_public_licences(project_id: str) -> List[str]:
  """Returns a list of licenses based on publicly available image project"""
  licenses = []
  gce_api = apis.get_api('compute', 'v1', project_id)
  logging.debug('listing licenses of project %s', project_id)
  request = gce_api.licenses().list(project=project_id)
  while request is not None:
    response = request.execute()
    for license_ in response['items']:
      formatted_license = license_['selfLink'].partition('/global/licenses/')[2]
      licenses.append(formatted_license)
    request = gce_api.licenses().list_next(previous_request=request,
                                           previous_response=response)
  return licenses


def get_instance(project_id: str, zone: str, instance_name: str) -> Instance:
  """Returns instance object matching instance name and zone"""
  compute = apis.get_api('compute', 'v1', project_id)
  request = compute.instances().get(project=project_id,
                                    zone=zone,
                                    instance=instance_name)

  response = request.execute(num_retries=config.API_RETRIES)
  return Instance(project_id, resource_data=response)


@caching.cached_api_call(in_memory=True)
def get_instance_by_id(project_id: str, instance_id: str) -> Optional[Instance]:
  """Returns instance object matching instance id in the project.

  Searches all zones.

  Args:
    project_id: The ID of the GCP project.
    instance_id: The unique ID of the GCE instance.
  """
  if not apis.is_enabled(project_id, 'compute'):
    return None
  gce_api = apis.get_api('compute', 'v1', project_id)
  # Use aggregatedList with filter to efficiently find the instance by ID.
  request = gce_api.instances().aggregatedList(project=project_id,
                                               filter=f'id eq {instance_id}',
                                               returnPartialSuccess=True)

  while request:
    response = request.execute(num_retries=config.API_RETRIES)
    items = response.get('items', {})
    for _, data in items.items():
      if 'instances' in data:
        for instance_data in data['instances']:
          if str(instance_data.get('id')) == str(instance_id):
            return Instance(project_id, instance_data)

    request = gce_api.instances().aggregatedList_next(
        previous_request=request, previous_response=response)

  return None


@caching.cached_api_call(in_memory=True)
def get_global_operations(
    project: str,
    filter_str: Optional[str] = None,
    order_by: Optional[str] = None,
    max_results: Optional[int] = None,
    service_project_number: Optional[int] = None,
) -> List[Dict[str, Any]]:
  """Returns global operations object matching project id."""
  compute = apis.get_api('compute', 'v1', project)
  logging.debug(('searching compute global operations'
                 'logs in project %s with filter %s'), project, filter_str)
  operations: List[Dict[str, Any]] = []
  request = compute.globalOperations().aggregatedList(
      project=project,
      filter=filter_str,
      orderBy=order_by,
      maxResults=max_results,
      serviceProjectNumber=service_project_number,
      returnPartialSuccess=True,
  )
  while request:
    response = request.execute(num_retries=config.API_RETRIES)
    operations_by_regions = response.get('items', {})
    for _, data in operations_by_regions.items():
      if 'operations' not in data:
        continue
      operations.extend(data['operations'])
    request = compute.globalOperations().aggregatedList_next(
        previous_request=request, previous_response=response)
  return operations


@caching.cached_api_call(in_memory=True)
def get_disk(project_id: str, zone: str, disk_name: str) -> Disk:
  """Returns disk object matching disk name and zone."""
  compute = apis.get_api('compute', 'v1', project_id)
  request = compute.disks().get(project=project_id, zone=zone, disk=disk_name)
  response = request.execute(num_retries=config.API_RETRIES)
  return Disk(project_id, resource_data=response)


def get_instance_group_manager(
    project_id: str, zone: str,
    instance_group_manager_name: str) -> ManagedInstanceGroup:
  """Get a zonal ManagedInstanceGroup object by name and zone.

  Args:
    project_id: The project ID of the instance group manager.
    zone: The zone of the instance group manager.
    instance_group_manager_name: The name of the instance group manager.

  Returns:
    A ManagedInstanceGroup object.

  Raises:
    utils.GcpApiError: If the API call fails.
  """
  compute = apis.get_api('compute', 'v1', project_id)
  request = compute.instanceGroupManagers().get(
      project=project_id,
      zone=zone,
      instanceGroupManager=instance_group_manager_name)
  try:
    response = request.execute(num_retries=config.API_RETRIES)
    return ManagedInstanceGroup(project_id, resource_data=response)
  except googleapiclient.errors.HttpError as err:
    raise utils.GcpApiError(err) from err


def get_region_instance_group_manager(
    project_id: str, region: str,
    instance_group_manager_name: str) -> ManagedInstanceGroup:
  """Get a regional ManagedInstanceGroup object by name and region.

  Args:
    project_id: The project ID of the instance group manager.
    region: The region of the instance group manager.
    instance_group_manager_name: The name of the instance group manager.

  Returns:
    A ManagedInstanceGroup object.

  Raises:
    utils.GcpApiError: If the API call fails.
  """
  compute = apis.get_api('compute', 'v1', project_id)
  request = compute.regionInstanceGroupManagers().get(
      project=project_id,
      region=region,
      instanceGroupManager=instance_group_manager_name,
  )
  try:
    response = request.execute(num_retries=config.API_RETRIES)
    return ManagedInstanceGroup(project_id, resource_data=response)
  except googleapiclient.errors.HttpError as err:
    raise utils.GcpApiError(err) from err


def get_autoscaler(project_id: str, zone: str,
                   autoscaler_name: str) -> Autoscaler:
  """Get a zonal Autoscaler object by name and zone."""
  compute = apis.get_api('compute', 'v1', project_id)
  request = compute.autoscalers().get(project=project_id,
                                      zone=zone,
                                      autoscaler=autoscaler_name)
  try:
    response = request.execute(num_retries=config.API_RETRIES)
    return Autoscaler(project_id, resource_data=response)
  except googleapiclient.errors.HttpError as err:
    raise utils.GcpApiError(err) from err


def get_region_autoscaler(project_id: str, region: str,
                          autoscaler_name: str) -> Autoscaler:
  """Get a regional Autoscaler object by name and region."""
  compute = apis.get_api('compute', 'v1', project_id)
  request = compute.regionAutoscalers().get(project=project_id,
                                            region=region,
                                            autoscaler=autoscaler_name)
  try:
    response = request.execute(num_retries=config.API_RETRIES)
    return Autoscaler(project_id, resource_data=response)
  except googleapiclient.errors.HttpError as err:
    raise utils.GcpApiError(err) from err


@caching.cached_api_call(in_memory=True)
def get_instances(context: models.Context) -> Mapping[str, Instance]:
  """Get a list of Instance matching the given context, indexed by instance id."""

  instances: Dict[str, Instance] = {}
  if not apis.is_enabled(context.project_id, 'compute'):
    return instances
  gce_api = apis.get_api('compute', 'v1', context.project_id)
  request = gce_api.instances().aggregatedList(project=context.project_id,
                                               returnPartialSuccess=True)
  logging.debug('listing gce instances of project %s', context.project_id)
  while request:  # Continue as long as there are pages
    response = request.execute(num_retries=config.API_RETRIES)
    instances_by_zones = response.get('items', {})
    for _, data_ in instances_by_zones.items():
      if 'instances' not in data_:
        continue
      for instance in data_['instances']:
        result = re.match(
            r'https://www.googleapis.com/compute/v1/projects/[^/]+/zones/([^/]+)/',
            instance['selfLink'],
        )
        if not result:
          logging.error(
              "instance %s selfLink didn't match regexp: %s",
              instance['id'],
              instance['selfLink'],
          )
          continue
        zone = result.group(1)
        labels = instance.get('labels', {})
        if not context.match_project_resource(
            resource=instance.get('name'), location=zone,
            labels=labels) and not context.match_project_resource(
                resource=instance.get('id'), location=zone, labels=labels):
          continue
        instances.update({
            instance['id']:
                Instance(project_id=context.project_id, resource_data=instance)
        })
    request = gce_api.instances().aggregatedList_next(
        previous_request=request, previous_response=response)
  return instances


@caching.cached_api_call(in_memory=True)
def get_instance_groups(context: models.Context) -> Mapping[str, InstanceGroup]:
  """Get a list of InstanceGroups matching the given context, indexed by name."""
  groups: Dict[str, InstanceGroup] = {}
  if not apis.is_enabled(context.project_id, 'compute'):
    return groups
  gce_api = apis.get_api('compute', 'v1', context.project_id)
  request = gce_api.instanceGroups().aggregatedList(project=context.project_id,
                                                    returnPartialSuccess=True)
  logging.debug('listing gce instance groups of project %s', context.project_id)
  while request:  # Continue as long as there are pages
    response = request.execute(num_retries=config.API_RETRIES)
    groups_by_zones = response.get('items', {})
    for _, data_ in groups_by_zones.items():
      if 'instanceGroups' not in data_:
        continue
      for group in data_['instanceGroups']:
        result = re.match(
            r'https://www.googleapis.com/compute/v1/projects/[^/]+/(zones|regions)/([^/]+)',
            group['selfLink'],
        )
        if not result:
          logging.error(
              "instance %s selfLink didn't match regexp: %s",
              group['id'],
              group['selfLink'],
          )
          continue
        location = result.group(2)
        labels = group.get('labels', {})
        resource = group.get('name', '')
        if not context.match_project_resource(
            location=location, labels=labels, resource=resource):
          continue
        instance_group = InstanceGroup(context.project_id, resource_data=group)
        groups[instance_group.full_path] = instance_group
    request = gce_api.instanceGroups().aggregatedList_next(
        previous_request=request, previous_response=response)
  return groups


@caching.cached_api_call(in_memory=True)
def get_managed_instance_groups(
    context: models.Context,) -> Mapping[int, ManagedInstanceGroup]:
  """Get a list of zonal ManagedInstanceGroups matching the given context, indexed by mig id."""

  migs: Dict[int, ManagedInstanceGroup] = {}
  if not apis.is_enabled(context.project_id, 'compute'):
    return migs
  gce_api = apis.get_api('compute', 'v1', context.project_id)
  request = gce_api.instanceGroupManagers().aggregatedList(
      project=context.project_id, returnPartialSuccess=True)
  logging.debug('listing zonal managed instance groups of project %s',
                context.project_id)
  while request:  # Continue as long as there are pages
    response = request.execute(num_retries=config.API_RETRIES)
    migs_by_zones = response.get('items', {})
    for _, data_ in migs_by_zones.items():
      if 'instanceGroupManagers' not in data_:
        continue
      for mig in data_['instanceGroupManagers']:
        result = re.match(
            r'https://www.googleapis.com/compute/v1/projects/[^/]+/(?:regions|zones)/([^/]+)/',
            mig['selfLink'],
        )
        if not result:
          logging.error(
              "mig %s selfLink didn't match regexp: %s",
              mig['name'],
              mig['selfLink'],
          )
          continue
        location = result.group(1)
        labels = mig.get('labels', {})
        resource = mig.get('name', '')
        if not context.match_project_resource(
            location=location, labels=labels, resource=resource):
          continue
        migs[mig['id']] = ManagedInstanceGroup(project_id=context.project_id,
                                               resource_data=mig)
    request = gce_api.instanceGroupManagers().aggregatedList_next(
        previous_request=request, previous_response=response)
  return migs


@caching.cached_api_call(in_memory=True)
def get_region_managed_instance_groups(
    context: models.Context,) -> Mapping[int, ManagedInstanceGroup]:
  """Get a list of regional ManagedInstanceGroups matching the given context, indexed by mig id."""

  migs: Dict[int, ManagedInstanceGroup] = {}
  if not apis.is_enabled(context.project_id, 'compute'):
    return migs
  gce_api = apis.get_api('compute', 'v1', context.project_id)
  requests = [
      gce_api.regionInstanceGroupManagers().list(project=context.project_id,
                                                 region=r.name)
      for r in get_all_regions(context.project_id)
  ]
  logging.debug(
      'listing regional managed instance groups of project %s',
      context.project_id,
  )
  items = apis_utils.execute_concurrently_with_pagination(
      api=gce_api,
      requests=requests,
      next_function=gce_api.regionInstanceGroupManagers().list_next,
      context=context,
      log_text=
      f'listing regional managed instance groups of project {context.project_id}'
  )
  for i in items:
    result = re.match(
        r'https://www.googleapis.com/compute/v1/projects/[^/]+/(?:regions)/([^/]+)/',
        i['selfLink'],
    )
    if not result:
      logging.error("mig %s selfLink didn't match regexp: %s", i['name'],
                    i['selfLink'])
      continue
    location = result.group(1)
    labels = i.get('labels', {})
    name = i.get('name', '')
    if not context.match_project_resource(
        location=location, labels=labels, resource=name):
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
      fields=('items/name, items/properties/tags,'
              ' items/properties/networkInterfaces,'
              ' items/properties/serviceAccounts, items/properties/metadata'),
  )
  for t in apis_utils.list_all(
      request, next_function=gce_api.instanceTemplates().list_next):
    instance_template = InstanceTemplate(project_id, t)
    templates[instance_template.full_path] = instance_template
  return templates


@caching.cached_api_call
def get_project_metadata(project_id) -> Mapping[str, str]:
  gce_api = apis.get_api('compute', 'v1', project_id)
  logging.debug('fetching metadata of project %s\n', project_id)
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


@caching.cached_api_call
def get_instances_serial_port_output(context: models.Context):
  """Get a list of serial port output for instances

  which matches the given context, running and is not
  exported to cloud logging.
  """
  # Create temp storage (diskcache.Deque) for output
  deque = caching.get_tmp_deque('tmp-gce-serial-output-')
  if not apis.is_enabled(context.project_id, 'compute'):
    return deque
  gce_api = apis.get_api('compute', 'v1', context.project_id)

  # Serial port output are rolled over on day 7 and limited to 1MB.
  # Fetching serial outputs are very expensive so optimize to fetch.
  # Only relevant instances as storage size can grow drastically for
  # massive projects. Think 1MB * N where N is some large number.
  requests = [
      gce_api.instances().getSerialPortOutput(
          project=i.project_id,
          zone=i.zone,
          instance=i.id,
          # To get all 1mb output
          start=-1000000,
      )
      for i in get_instances(context).values()
      # fetch running instances that do not export to cloud logging
      if not i.is_serial_port_logging_enabled() and i.is_running
  ]
  requests_start_time = datetime.now()
  # Note: We are limited to 1000 calls in a single batch request.
  # We have to use multiple batch requests in batches of 1000
  # https://github.com/googleapis/google-api-python-client/blob/main/docs/batch.md
  batch_size = 1000
  for i in range(0, len(requests), batch_size):
    batch_requests = requests[i:i + batch_size]
    for _, response, exception in apis_utils.execute_concurrently(
        api=gce_api, requests=batch_requests, context=context):
      if exception:
        if isinstance(exception, googleapiclient.errors.HttpError):
          raise utils.GcpApiError(exception) from exception
        else:
          raise exception

      if response:
        result = re.match(
            r'https://www.googleapis.com/compute/v1/projects/([^/]+)/zones/[^/]+/instances/([^/]+)',
            response['selfLink'],
        )
        if not result:
          logging.error("instance selfLink didn't match regexp: %s",
                        response['selfLink'])
          return

        project_id = result.group(1)
        instance_id = result.group(2)
        deque.appendleft(
            SerialPortOutput(
                project_id=project_id,
                instance_id=instance_id,
                contents=response['contents'].splitlines(),
            ))
  requests_end_time = datetime.now()
  logging.debug(
      'total serial logs processing time: %s, number of instances: %s',
      requests_end_time - requests_start_time,
      len(requests),
  )
  return deque


@caching.cached_api_call
def get_instance_serial_port_output(
    project_id, zone, instance_name) -> Optional[SerialPortOutput]:
  """Get a list of serial port output for instances

  which matches the given context, running and is not
  exported to cloud logging.
  """
  # Create temp storage (diskcache.Deque) for output
  if not apis.is_enabled(project_id, 'compute'):
    return None
  gce_api = apis.get_api('compute', 'v1', project_id)

  request = gce_api.instances().getSerialPortOutput(
      project=project_id,
      zone=zone,
      instance=instance_name,
      # To get all 1mb output
      start=-1000000,
  )
  try:
    response = request.execute(num_retries=config.API_RETRIES)
  except googleapiclient.errors.HttpError:
    return None

  if response:
    result = re.match(
        r'https://www.googleapis.com/compute/v1/projects/([^/]+)/zones/[^/]+/instances/([^/]+)',
        response['selfLink'],
    )
    if not result:
      logging.error("instance selfLink didn't match regexp: %s",
                    response['selfLink'])
      return None

    project_id = result.group(1)
    instance_id = result.group(2)
    return SerialPortOutput(
        project_id,
        instance_id=instance_id,
        contents=response['contents'].splitlines(),
    )
  return None


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
def get_all_disks(context: models.Context) -> Iterable[Disk]:
  """Get all disks in a project, matching the context.

  Args:
    context: The project context.

  Returns:
    An iterable of Disk objects.
  """
  project_id = context.project_id
  # Fetching only Zonal Disks(Regional disks exempted)
  try:
    gce_api = apis.get_api('compute', 'v1', project_id)
    requests = [
        gce_api.disks().list(project=project_id, zone=zone)
        for zone in get_gce_zones(project_id)
    ]

    logging.debug('listing gce disks of project %s', project_id)

    items = apis_utils.execute_concurrently_with_pagination(
        api=gce_api,
        requests=requests,
        next_function=gce_api.disks().list_next,
        context=context,
        log_text=f'listing GCE disks of project {project_id}')

    return {Disk(project_id, item) for item in items}

  except googleapiclient.errors.HttpError as err:
    raise utils.GcpApiError(err) from err


@caching.cached_api_call
def get_all_disks_of_instance(context: models.Context, zone: str,
                              instance_name: str) -> dict:
  """Get all disks of a given instance.

  Args:
    context: The project context.
    zone: The zone of the instance.
    instance_name: The name of the instance.

  Returns:
    A dict of Disk objects keyed by disk name.
  """
  project_id = context.project_id
  # Fetching only Zonal Disks(Regional disks exempted) attached to an instance
  try:
    gce_api = apis.get_api('compute', 'v1', project_id)
    requests = [gce_api.disks().list(project=project_id, zone=zone)]
    logging.debug(
        'listing gce disks attached to instance %s in project %s',
        instance_name,
        project_id,
    )

    items = apis_utils.execute_concurrently_with_pagination(
        api=gce_api,
        requests=requests,
        next_function=gce_api.disks().list_next,
        context=context,
        log_text=
        f'listing gce disks attached to instance {instance_name} in project {project_id}'
    )
    all_disk_list = {Disk(project_id, item) for item in items}
    disk_list = {}
    for disk in all_disk_list:
      if disk.users == [instance_name]:
        disk_list[disk.name] = disk
    return disk_list

  except googleapiclient.errors.HttpError as err:
    raise utils.GcpApiError(err) from err


class InstanceEffectiveFirewalls(network_q.EffectiveFirewalls):
  """Effective firewall rules for a network interface on a VM instance.

  Includes org/folder firewall policies).
  """

  _instance: Instance
  _nic: str

  def __init__(self, instance, nic, resource_data):
    super().__init__(resource_data)
    self._instance = instance
    self._nic = nic


@caching.cached_api_call(in_memory=True)
def get_instance_interface_effective_firewalls(
    instance: Instance, nic: str) -> InstanceEffectiveFirewalls:
  """Return effective firewalls for a network interface on the instance."""
  compute = apis.get_api('compute', 'v1', instance.project_id)
  request = compute.instances().getEffectiveFirewalls(
      project=instance.project_id,
      zone=instance.zone,
      instance=instance.name,
      networkInterface=nic,
  )
  response = request.execute(num_retries=config.API_RETRIES)
  return InstanceEffectiveFirewalls(Instance, nic, response)


def is_project_serial_port_logging_enabled(project_id: str) -> bool:
  if not apis.is_enabled(project_id, 'compute'):
    return False

  value = get_project_metadata(
      project_id=project_id).get('serial-port-logging-enable')
  return bool(value and value.upper() in POSITIVE_BOOL_VALUES)


def is_serial_port_buffer_enabled():
  return config.get('enable_gce_serial_buffer')


@dataclasses.dataclass
class _SerialOutputJob:
  """A group of log queries that will be executed with a single API call."""

  context: models.Context
  future: Optional[concurrent.futures.Future] = None

  def __init__(self,
               context,
               future: Optional[concurrent.futures.Future] = None):
    self.context = context
    self.future = future


class SerialOutputQuery:
  """A serial output job that was started with prefetch_logs()."""

  job: _SerialOutputJob

  def __init__(self, job):
    self.job = job

  @property
  def entries(self) -> Sequence:
    if not self.job.future:
      raise RuntimeError("Fetching serial logs wasn't executed. did you call"
                         ' execute_get_serial_port_output()?')
    elif self.job.future.running():
      logging.debug(
          'waiting for serial output results for project: %s',
          self.job.context.project_id,
      )
    return self.job.future.result()


jobs_todo: Dict[models.Context, _SerialOutputJob] = {}


def execute_fetch_serial_port_outputs(
    query_executor: executor.ContextAwareExecutor):
  # start a thread to fetch serial log; processing logs can be large
  # depending on he number of instances in the project which aren't
  # logging to cloud logging. currently expects only one job but
  # implementing it so support for multiple projects is possible.
  global jobs_todo
  jobs_executing = jobs_todo
  jobs_todo = {}
  # query_executor = get_executor(context)
  for job in jobs_executing.values():
    job.future = query_executor.submit(get_instances_serial_port_output,
                                       job.context)


def fetch_serial_port_outputs(context: models.Context) -> SerialOutputQuery:
  # Aggregate by context
  job = jobs_todo.setdefault(context, _SerialOutputJob(context=context))
  return SerialOutputQuery(job=job)


# Health check implementation
class HealthCheck(models.Resource):
  """A Health Check resource."""

  _resource_data: dict
  _type: str

  def __init__(self, project_id, resource_data):
    super().__init__(project_id=project_id)
    self._resource_data = resource_data

  @property
  def name(self) -> str:
    return self._resource_data['name']

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
  def is_log_enabled(self) -> bool:
    try:
      log_config = self._resource_data.get('logConfig', False)
      if log_config and log_config['enable']:
        return True
    except KeyError:
      return False
    return False

  @property
  def region(self):
    url = self._resource_data.get('region', '')
    match = re.search(r'/([^/]+)/?$', url)
    if match:
      region = match.group(1)
      return region
    return None

  @property
  def type(self) -> str:
    return self._resource_data['type']

  @property
  def request_path(self) -> str:
    return self.get_health_check_property('requestPath', '/')

  @property
  def request(self) -> str:
    return self.get_health_check_property('request')

  @property
  def response(self) -> str:
    return self.get_health_check_property('response')

  @property
  def port(self) -> int:
    return self.get_health_check_property('port')

  @property
  def port_specification(self) -> str:
    return self.get_health_check_property('portSpecification', 'USE_FIXED_PORT')

  @property
  def timeout_sec(self) -> int:
    return self._resource_data.get('timeoutSec', 5)

  @property
  def check_interval_sec(self) -> int:
    return self._resource_data.get('checkIntervalSec', 5)

  @property
  def unhealthy_threshold(self) -> int:
    return self._resource_data.get('unhealthyThreshold', 2)

  @property
  def healthy_threshold(self) -> int:
    return self._resource_data.get('healthyThreshold', 2)

  def get_health_check_property(self, property_name: str, default_value=None):
    health_check_types = {
        'HTTP': 'httpHealthCheck',
        'HTTPS': 'httpsHealthCheck',
        'HTTP2': 'http2HealthCheck',
        'TCP': 'tcpHealthCheck',
        'SSL': 'sslHealthCheck',
        'GRPC': 'grpcHealthCheck',
    }
    if self.type in health_check_types:
      health_check_data = self._resource_data.get(health_check_types[self.type])
      if health_check_data:
        return health_check_data.get(property_name) or default_value
    return default_value


@caching.cached_api_call(in_memory=True)
def get_health_check(project_id: str,
                     health_check: str,
                     region: str = None) -> object:
  compute = apis.get_api('compute', 'v1', project_id)
  if not region or region == 'global':
    request = compute.healthChecks().get(project=project_id,
                                         healthCheck=health_check)
  else:
    request = compute.regionHealthChecks().get(project=project_id,
                                               healthCheck=health_check,
                                               region=region)
  response = request.execute(num_retries=config.API_RETRIES)
  return HealthCheck(project_id, response)


class NetworkEndpointGroup(models.Resource):
  """A Network Endpoint Group resource."""

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


@caching.cached_api_call(in_memory=True)
def get_zonal_network_endpoint_groups(
    context: models.Context,) -> Mapping[str, NetworkEndpointGroup]:
  """Returns a list of Network Endpoint Groups in the project."""
  groups: Dict[str, NetworkEndpointGroup] = {}
  if not apis.is_enabled(context.project_id, 'compute'):
    return groups
  gce_api = apis.get_api('compute', 'v1', context.project_id)
  requests = [
      gce_api.networkEndpointGroups().list(project=context.project_id,
                                           zone=zone)
      for zone in get_gce_zones(context.project_id)
  ]
  logging.debug('listing gce networkEndpointGroups of project %s',
                context.project_id)
  items = apis_utils.execute_concurrently_with_pagination(
      api=gce_api,
      requests=requests,
      next_function=gce_api.networkEndpointGroups().list_next,
      context=context,
      log_text=(
          f'listing gce networkEndpointGroups of project {context.project_id}'),
  )

  for i in items:
    result = re.match(
        r'https://www.googleapis.com/compute/v1/projects/[^/]+/zones/([^/]+)',
        i['selfLink'],
    )
    if not result:
      logging.error("instance %s selfLink didn't match regexp: %s", i['id'],
                    i['selfLink'])
      continue
    zone = result.group(1)
    labels = i.get('labels', {})
    resource = i.get('name', '')
    if not context.match_project_resource(
        location=zone, labels=labels, resource=resource):
      continue
    data = NetworkEndpointGroup(context.project_id, i)
    groups[data.full_path] = data
  return groups
