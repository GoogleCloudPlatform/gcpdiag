# Lint as: python3
"""Queries related to GCP Kubernetes Engine clusters."""

import ipaddress
import logging
import re
from typing import Dict, Iterable, List, Mapping, Optional

import googleapiclient.errors

from gcp_doctor import cache, config, models, utils
from gcp_doctor.queries import apis, gce


class NodePool(models.Resource):
  """Represents a GKE node pool."""

  def __init__(self, cluster, resource_data):
    super().__init__(project_id=cluster.project_id)
    self._cluster = cluster
    self._resource_data = resource_data
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
      return f'{self.project_nr}-compute@developer.gserviceaccount.com'
    else:
      return sa

  @property
  def version(self) -> str:
    return self._resource_data['version']

  @property
  def pod_ipv4_cidr_size(self) -> int:
    return self._resource_data['podIpv4CidrSize']

  @property
  def cluster(self) -> 'Cluster':
    return self._cluster

  @property
  def instance_groups(self) -> List[gce.ManagedInstanceGroup]:
    if self._migs is None:
      project_migs_by_selflink = dict()
      for m in gce.get_managed_instance_groups(
          models.Context(projects=[self.project_id])).values():
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

  def __init__(self, project_id, resource_data):
    super().__init__(project_id=project_id)
    self._resource_data = resource_data
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
  def master_version(self) -> str:
    return self._resource_data['currentMasterVersion']

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


@cache.cached_api_call
def get_clusters(context: models.Context) -> Mapping[str, Cluster]:
  """Get a list of Cluster matching the given context, indexed by cluster name."""
  clusters: Dict[str, Cluster] = {}
  container_api = apis.get_api('container', 'v1')
  for project_id in context.projects:
    logging.info('fetching list of GKE clusters in project %s', project_id)
    query = container_api.projects().locations().clusters().list(
        parent=f'projects/{project_id}/locations/-')
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
        c = Cluster(project_id=project_id, resource_data=resp_c)
        clusters[c.full_path] = c
    except googleapiclient.errors.HttpError as err:
      errstr = utils.http_error_message(err)
      # TODO: implement proper exception classes
      raise ValueError(
          f'can\'t list clusters for project {project_id}: {errstr}') from err
  return clusters


@cache.cached_api_call
def _get_server_config(project_id: str, location: str):
  container_api = apis.get_api('container', 'v1')
  name = f'projects/{project_id}/locations/{location}'
  request = container_api.projects().locations().getServerConfig(name=name)
  try:
    resp = request.execute(num_retries=config.API_RETRIES)
    return resp
  except googleapiclient.errors.HttpError as err:
    errstr = utils.http_error_message(err)
    raise ValueError(
        f'can\'t get gke version list for project {project_id}: {errstr}'
    ) from err


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
