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

import functools
import ipaddress
import logging
import re
from typing import Dict, Iterable, List, Mapping, Optional

import googleapiclient.errors

from gcpdiag import caching, config, models, utils
from gcpdiag.queries import apis, crm, gce


class VersionComponentsParser:
  """ Simple helper class to parse version string to components """

  version_str: str

  def __init__(self, version_str: str):
    self.version_str = str(version_str)

  def get_components(self) -> List[int]:
    cs = [int(s) for s in self.extract_base_version().split('.')]
    # example: 1 -> 1.0.0, 1.2 -> 1.2.0
    cs += [0] * (3 - len(cs))
    return cs

  def extract_base_version(self) -> str:
    m = re.search(r'^[\d\.]+', self.version_str)
    if m is None:
      raise Exception(f'Can not parse version {self.version_str}')
    return m.group(0)


class Version:
  """ Represents GKE Version """

  version_str: str
  major: int
  minor: int
  patch: int

  def __init__(self, version_str: str):
    # example: 1.19.13-gke.701
    self.version_str = version_str
    self.major, self.minor, self.patch = \
      VersionComponentsParser(version_str).get_components()

  def same_major(self, other_version: 'Version') -> bool:
    return self.major == other_version.major

  def diff_minor(self, other_version: 'Version') -> int:
    return abs(self.minor - other_version.minor)

  def __str__(self) -> str:
    return self.version_str

  def __add__(self, other: object) -> object:
    if isinstance(other, str):
      return self.version_str + other
    raise TypeError(f'Can not concatenate Version and {type(other)}')

  def __radd__(self, other: object) -> object:
    if isinstance(other, str):
      return other + self.version_str
    raise TypeError(f'Can not concatenate and {type(other)} Version')

  def __eq__(self, other: object) -> bool:
    if isinstance(other, str):
      return other == self.version_str
    if isinstance(other, Version):
      return self.version_str == other.version_str
    raise AttributeError('Can not compare Version object with {}'.format(
        type(other)))

  def __lt__(self, other):
    return self.major < other.major or self.minor < other.minor or self.patch < other.patch

  def __ge__(self, other):
    return self.major >= other.major and self.minor >= other.minor and self.patch >= other.patch


class NodeConfig:
  """Represents a GKE node pool configuration."""

  def __init__(self, resource_data):
    self._resource_data = resource_data

  @property
  def image_type(self) -> str:
    return self._resource_data['imageType']


class NodePool(models.Resource):
  """Represents a GKE node pool."""

  version: Version

  def __init__(self, cluster, resource_data):
    super().__init__(project_id=cluster.project_id)
    self._cluster = cluster
    self._resource_data = resource_data
    self.version = Version(self._resource_data['version'])
    self._migs = None

  def _get_service_account(self) -> str:
    return self._resource_data.get('config', {}).get('serviceAccount', None)

  @property
  def full_path(self) -> str:
    # https://container.googleapis.com/v1/projects/gcpd-gke-1-9b90/
    #   locations/europe-west1/clusters/gke2/nodePools/default-pool
    m = re.match(r'https://container.googleapis.com/v1/(.*)',
                 self._resource_data.get('selfLink', ''))
    if not m:
      raise RuntimeError('can\'t parse selfLink of nodepool resource')
    return m.group(1)

  @property
  def short_path(self) -> str:
    path = self.full_path
    path = re.sub(r'^projects/', '', path)
    path = re.sub(r'/locations/', '/', path)
    path = re.sub(r'/zones/', '/', path)
    path = re.sub(r'/clusters/', '/', path)
    path = re.sub(r'/nodePools/', '/', path)
    return path

  @property
  def name(self) -> str:
    return self._resource_data['name']

  @property
  def config(self) -> NodeConfig:
    return NodeConfig(self._resource_data['config'])

  def has_default_service_account(self) -> bool:
    sa = self._get_service_account()
    return sa == 'default'

  def has_workload_identity_enabled(self) -> bool:
    # Empty ({}) workloadMetadataConfig means that 'Metadata concealment'
    # (predecessor of Workload Identity) is enabled. That doesn't protect the
    # default SA's token
    # https://cloud.google.com/kubernetes-engine/docs/how-to/protecting-cluster-metadata#concealment
    return 'config' in self._resource_data and bool(
        self._resource_data['config'].get('workloadMetadataConfig'))

  @property
  def service_account(self) -> str:
    sa = self._get_service_account()
    if sa == 'default':
      project_nr = crm.get_project(self.project_id).number
      return f'{project_nr}-compute@developer.gserviceaccount.com'
    else:
      return sa

  @property
  def pod_ipv4_cidr_size(self) -> int:
    return self._resource_data['podIpv4CidrSize']

  @property
  def cluster(self) -> 'Cluster':
    return self._cluster

  @property
  def instance_groups(self) -> List[gce.ManagedInstanceGroup]:
    if self._migs is None:
      project_migs_by_selflink = {}
      for m in gce.get_managed_instance_groups(
          models.Context(project_id=self.project_id)).values():
        project_migs_by_selflink[m.self_link] = m

      self._migs = []
      for url in self._resource_data.get('instanceGroupUrls', []):
        try:
          self._migs.append(project_migs_by_selflink[url])
        except KeyError:
          continue

    return self._migs


class Cluster(models.Resource):
  """Represents a GKE cluster.

  https://cloud.google.com/kubernetes-engine/docs/reference/rest/v1/projects.locations.clusters#Cluster
  """
  _resource_data: dict
  master_version: Version

  def __init__(self, project_id, resource_data):
    super().__init__(project_id=project_id)
    self._resource_data = resource_data
    self.master_version = Version(self._resource_data['currentMasterVersion'])
    self._nodepools = None

  @property
  def full_path(self) -> str:
    if utils.is_region(self._resource_data['location']):
      return (f'projects/{self.project_id}/'
              f'locations/{self.location}/clusters/{self.name}')
    else:
      return (f'projects/{self.project_id}/'
              f'zones/{self.location}/clusters/{self.name}')

  @property
  def short_path(self) -> str:
    path = self.full_path
    path = re.sub(r'^projects/', '', path)
    path = re.sub(r'/locations/', '/', path)
    path = re.sub(r'/zones/', '/', path)
    path = re.sub(r'/clusters/', '/', path)
    return path

  @property
  def name(self) -> str:
    return self._resource_data['name']

  @property
  def location(self) -> str:
    return self._resource_data['location']

  @property
  def pod_ipv4_cidr(self) -> ipaddress.IPv4Address:
    cidr = self._resource_data['clusterIpv4Cidr']
    return ipaddress.ip_network(cidr)

  @property
  def current_node_count(self) -> int:
    return self._resource_data.get('currentNodeCount', 0)

  @property
  def release_channel(self) -> Optional[str]:
    try:
      return self._resource_data['releaseChannel']['channel']
    except KeyError:
      return None

  @property
  def app_layer_sec_key(self) -> str:
    return self._resource_data['databaseEncryption'].get('keyName')

  def has_app_layer_enc_enabled(self) -> bool:
    # state := 'DECRYPTED' | 'ENCRYPTED', keyName := 'full_path_to_key_resouce'
    return 'databaseEncryption' in self._resource_data and \
           self._resource_data['databaseEncryption'].get('state') == 'ENCRYPTED'

  def has_logging_enabled(self) -> bool:
    return self._resource_data['loggingService'] != 'none'

  def has_monitoring_enabled(self) -> bool:
    return self._resource_data['monitoringService'] != 'none'

  @property
  def nodepools(self) -> Iterable[NodePool]:
    if self._nodepools is None:
      self._nodepools = []
      for n in self._resource_data.get('nodePools', []):
        self._nodepools.append(NodePool(self, n))
    return self._nodepools


@caching.cached_api_call
def get_clusters(context: models.Context) -> Mapping[str, Cluster]:
  """Get a list of Cluster matching the given context, indexed by cluster name."""
  clusters: Dict[str, Cluster] = {}
  if not apis.is_enabled(context.project_id, 'container'):
    return clusters
  container_api = apis.get_api('container', 'v1', context.project_id)
  logging.info('fetching list of GKE clusters in project %s',
               context.project_id)
  query = container_api.projects().locations().clusters().list(
      parent=f'projects/{context.project_id}/locations/-')
  try:
    resp = query.execute(num_retries=config.API_RETRIES)
    if 'clusters' not in resp:
      return clusters
    for resp_c in resp['clusters']:
      # verify that we some minimal data that we expect
      if 'name' not in resp_c or 'location' not in resp_c:
        raise RuntimeError(
            'missing data in projects.locations.clusters.list response')
      if not context.match_project_resource(
          location=resp_c['location'], labels=resp_c.get('resourceLabels')):
        continue
      c = Cluster(project_id=context.project_id, resource_data=resp_c)
      clusters[c.full_path] = c
  except googleapiclient.errors.HttpError as err:
    raise utils.GcpApiError(err) from err
  return clusters


@caching.cached_api_call
def _get_server_config(project_id: str, location: str):
  container_api = apis.get_api('container', 'v1', project_id)
  name = f'projects/{project_id}/locations/{location}'
  request = container_api.projects().locations().getServerConfig(name=name)
  try:
    resp = request.execute(num_retries=config.API_RETRIES)
    return resp
  except googleapiclient.errors.HttpError as err:
    raise utils.GcpApiError(err) from err


def get_valid_master_versions(project_id: str, location: str) -> List[str]:
  """Get a list of valid GKE master versions."""
  server_config = _get_server_config(project_id, location)
  versions: List[str] = []

  # channel versions may extend the list of all available versions.\
  # Especially for the Rapid channel - many new versions only available in Rapid
  # channel and not as a static version to make sure nobody stuck on that
  # version for an extended period of time.
  for c in server_config['channels']:
    versions += c['validVersions']

  versions += server_config['validMasterVersions']

  return versions


def get_valid_node_versions(project_id: str, location: str) -> List[str]:
  """Get a list of valid GKE master versions."""
  server_config = _get_server_config(project_id, location)
  versions: List[str] = []

  # See explanaition in get_valid_master_versions
  for c in server_config['channels']:
    versions += c['validVersions']

  versions += server_config['validNodeVersions']

  return versions


class Node(models.Resource):
  """Represents a GKE node.

  This class useful for example to determine the GKE cluster when you only have
  an GCE instance id (like from a metrics label). """

  instance: gce.Instance
  nodepool: NodePool
  mig: gce.ManagedInstanceGroup

  def __init__(self, instance, nodepool, mig):
    super().__init__(project_id=instance.project_id)
    self.instance = instance
    self.nodepool = nodepool
    self.mig = mig
    pass

  @property
  def full_path(self) -> str:
    return self.nodepool.cluster.full_path + '/nodes/' + self.instance.name

  @property
  def short_path(self) -> str:
    #return self.nodepool.cluster.short_path + '/' + self.instance.name
    return self.instance.short_path


# Note: we don't use caching.cached_api_call here to avoid the locking
# overhead. which is not required because all API calls are wrapper already
# around caching.cached_api_call.
@functools.lru_cache()
def get_node_by_instance_id(context: models.Context, instance_id: str) -> Node:
  """Get a gke.Node instance by instance id.

  Throws a KeyError in case this instance is not found or isn't part of a GKE cluster.
  """
  # This will throw a KeyError if the instance is not found, which is also
  # the behavior that we want for this function.
  instance = gce.get_instances(context)[instance_id]
  clusters = get_clusters(context)
  try:
    # instance.mig throws AttributeError if it isn't part of a mig
    mig = instance.mig

    # find a NodePool that uses this MIG
    for c in clusters.values():
      for np in c.nodepools:
        for np_mig in np.instance_groups:
          if mig == np_mig:
            return Node(instance=instance, nodepool=np, mig=mig)

    # if we didn't find a nodepool that owns this instance, raise a KeyError
    raise KeyError('can\'t determine GKE cluster for instance %s' %
                   (instance_id))

  except AttributeError as err:
    raise KeyError from err
  return None
