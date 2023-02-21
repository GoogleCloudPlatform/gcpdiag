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
from boltons.iterutils import get_path

from gcpdiag import caching, config, models, utils
from gcpdiag.queries import apis, crm, gce, network
from gcpdiag.utils import Version


class NodeConfig:
  """Represents a GKE node pool configuration."""

  def __init__(self, resource_data):
    self._resource_data = resource_data

  def has_accelerators(self) -> bool:
    if 'accelerators' in self._resource_data:
      return True
    return False

  @property
  def machine_type(self) -> str:
    return self._resource_data['machineType']

  @property
  def image_type(self) -> str:
    return self._resource_data['imageType']

  @property
  def oauth_scopes(self) -> list:
    return self._resource_data['oauthScopes']


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
    # https://container.googleapis.com/v1/projects/gcpdiag-gke1-aaaa/
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

  @property
  def node_count(self) -> int:
    return self._resource_data.get('initialNodeCount', 0)

  def has_default_service_account(self) -> bool:
    sa = self._get_service_account()
    return sa == 'default'

  def has_image_streaming_enabled(self) -> bool:
    return get_path(self._resource_data, ('config', 'gcfsConfig', 'enabled'),
                    default=False)

  def has_md_concealment_enabled(self) -> bool:
    # Empty ({}) workloadMetadataConfig means that 'Metadata concealment'
    # (predecessor of Workload Identity) is enabled.
    # https://cloud.google.com/kubernetes-engine/docs/how-to/protecting-cluster-metadata#concealment
    return get_path(self._resource_data, ('config', 'workloadMetadataConfig'),
                    default=None) == {}

  def has_workload_identity_enabled(self) -> bool:
    # 'Metadata concealment' (workloadMetadataConfig == {}) doesn't protect the
    # default SA's token
    return bool(
        get_path(self._resource_data, ('config', 'workloadMetadataConfig'),
                 default=None))

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

  @property
  def node_tags(self) -> List[str]:
    """Returns the firewall tags used for nodes in this cluster.

    If the node tags can't be determined, [] is returned.
    """
    migs = self.instance_groups
    if not migs:
      return []
    return migs[0].template.tags

  def get_machine_type(self) -> str:
    """Returns the machine type of the nodepool nodes"""
    return self.config.machine_type


class UndefinedClusterPropertyError(Exception):
  """Thrown when a property of a cluster can't be determined for
  some reason. For example, the cluster_hash can't be determined
  because there are no nodepools defined."""
  pass


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
  def pod_ipv4_cidr(self) -> ipaddress.IPv4Network:
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
  def nap_node_image_type(self) -> Optional[str]:

    return get_path(
        self._resource_data,
        ('autoscaling', 'autoprovisioningNodePoolDefaults', 'imageType'),
        default=None)

  @property
  def app_layer_sec_key(self) -> str:
    return self._resource_data['databaseEncryption'].get('keyName')

  def has_app_layer_enc_enabled(self) -> bool:
    # state := 'DECRYPTED' | 'ENCRYPTED', keyName := 'full_path_to_key_resouce'
    return get_path(self._resource_data, ('databaseEncryption', 'state'),
                    default=None) == 'ENCRYPTED'

  def has_logging_enabled(self) -> bool:
    return self._resource_data['loggingService'] != 'none'

  def has_monitoring_enabled(self) -> bool:
    return self._resource_data['monitoringService'] != 'none'

  def has_authenticator_group_enabled(self) -> bool:
    return len(self._resource_data.get('authenticatorGroupsConfig', {})) > 0

  def has_workload_identity_enabled(self) -> bool:
    return len(self._resource_data.get('workloadIdentityConfig', {})) > 0

  def has_http_load_balancing_enabled(self) -> bool:
    # HTTP load balancing needs to be enabled to use GKE ingress
    return not (get_path(self._resource_data,
                         ('addonsConfig', 'httpLoadBalancing', 'disabled'),
                         default=None) is True)

  def has_network_policy_enabled(self) -> bool:
    # Network policy enforcement
    return not (get_path(self._resource_data,
                         ('addonsConfig', 'networkPolicyConfig', 'disabled'),
                         default=False) is True)

  def has_dpv2_enabled(self) -> bool:
    # Checks whether dataplane V2 is enabled in clusters
    return (get_path(self._resource_data, ('networkConfig', 'datapathProvider'),
                     default=None) == 'ADVANCED_DATAPATH')

  def has_intra_node_visibility_enabled(self) -> bool:
    if ('networkConfig' in self._resource_data and
        'enableIntraNodeVisibility' in self._resource_data['networkConfig']):
      return self._resource_data['networkConfig']['enableIntraNodeVisibility']
    return False

  def has_maintenance_window(self) -> bool:
    # 'e3b0c442' is a hexadecimal string that represents the value of an empty
    # string ('') in cryptography. If the maintenance windows are defined, the
    # value of 'resourceVersion' is not empty ('e3b0c442').
    return self._resource_data['maintenancePolicy'][
        'resourceVersion'] != 'e3b0c442'

  def has_image_streaming_enabled(self) -> bool:
    """
    Check if cluster has Image Streaming (aka  Google Container File System)
    enabled
    """
    global_gcsfs = get_path(
        self._resource_data,
        ('nodePoolDefaults', 'nodeConfigDefaults', 'gcfsConfig', 'enabled'),
        default=False)
    # Check nodePoolDefaults settings
    if global_gcsfs:
      return True
    for np in self.nodepools:
      # Check if any nodepool has image streaming enabled
      if np.has_image_streaming_enabled():
        return True
    return False

  @property
  def nodepools(self) -> Iterable[NodePool]:
    if self._nodepools is None:
      self._nodepools = []
      for n in self._resource_data.get('nodePools', []):
        self._nodepools.append(NodePool(self, n))
    return self._nodepools

  @property
  def network(self) -> network.Network:
    # projects/gcpdiag-gke1-aaaa/global/networks/default
    network_string = self._resource_data['networkConfig']['network']
    m = re.match(r'projects/([^/]+)/global/networks/([^/]+)$', network_string)
    if not m:
      raise RuntimeError("can't parse network string: %s" % network_string)
    return network.get_network(m.group(1), m.group(2))

  @property
  def subnetwork(self) -> Optional[models.Resource]:
    # 'projects/gcpdiag-gke1-aaaa/regions/europe-west4/subnetworks/default'
    if 'subnetwork' not in self._resource_data['networkConfig']:
      return None

    subnetwork_string = self._resource_data['networkConfig']['subnetwork']
    m = re.match(r'projects/([^/]+)/regions/([^/]+)/subnetworks/([^/]+)$',
                 subnetwork_string)
    if not m:
      raise RuntimeError("can't parse network string: %s" % subnetwork_string)
    return network.get_subnetwork(m.group(1), m.group(2), m.group(3))

  @property
  def is_private(self) -> bool:
    if not 'privateClusterConfig' in self._resource_data:
      return False

    return self._resource_data['privateClusterConfig'].get(
        'enablePrivateNodes', False)

  @property
  def is_vpc_native(self) -> bool:
    return self._resource_data['ipAllocationPolicy'].get('useIpAliases', False)

  @property
  def is_regional(self) -> bool:
    return len(self._resource_data['locations']) > 1

  @property
  def is_autopilot(self) -> bool:
    if not 'autopilot' in self._resource_data:
      return False
    return self._resource_data['autopilot'].get('enabled', False)

  @property
  def masters_cidr_list(self) -> Iterable[ipaddress.IPv4Network]:
    if get_path(self._resource_data,
                ('privateClusterConfig', 'masterIpv4CidrBlock'),
                default=None):
      return [
          ipaddress.ip_network(self._resource_data['privateClusterConfig']
                               ['masterIpv4CidrBlock'])
      ]
    else:
      if self.current_node_count and not self.cluster_hash:
        logging.warning("couldn't retrieve cluster hash for cluster %s.",
                        self.name)
        return []
      fw_rule_name = f'gke-{self.name}-{self.cluster_hash}-ssh'
      rule = self.network.firewall.get_vpc_ingress_rules(name=fw_rule_name)
      if rule and rule[0].is_enabled():
        return rule[0].source_ranges
      return []

  @property
  def cluster_hash(self) -> Optional[str]:
    """Returns the "cluster hash" as used in automatic firewall rules for GKE clusters.
    Cluster hash is the first 8 characters of cluster id.
    See also: https://cloud.google.com/kubernetes-engine/docs/concepts/firewall-rules
    """
    if 'id' in self._resource_data:
      return self._resource_data['id'][:8]
    raise UndefinedClusterPropertyError('no id')


@caching.cached_api_call
def get_clusters(context: models.Context) -> Mapping[str, Cluster]:
  """Get a list of Cluster matching the given context, indexed by cluster full path."""
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
