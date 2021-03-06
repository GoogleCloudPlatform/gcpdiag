# Lint as: python3
"""Queries related to GCP Kubernetes Engine clusters."""

import functools
import logging
import re
from typing import Dict, Iterable, List, Mapping

import googleapiclient.errors

from gcp_doctor import config, models, utils
from gcp_doctor.queries import apis


class NodePool(models.Resource):
  """Represents a GKE node pool."""

  def __init__(self, project_id, resource_data):
    super().__init__(project_id=project_id)
    self._resource_data = resource_data

  def _get_service_account(self) -> str:
    return self._resource_data.get('config', {}).get('serviceAccount', None)

  def get_full_path(self) -> str:
    # https://container.googleapis.com/v1/projects/gcpd-gke-1-9b90/
    #   locations/europe-west1/clusters/gke2/nodePools/default-pool
    m = re.match(r'https://container.googleapis.com/v1/(.*)',
                 self._resource_data.get('selfLink', ''))
    if not m:
      raise RuntimeError('can\'t parse selfLink of nodepool resource')
    return m.group(1)

  def get_short_path(self) -> str:
    path = self.get_full_path()
    path = re.sub(r'^projects/', '', path)
    path = re.sub(r'/locations/', '/', path)
    path = re.sub(r'/zones/', '/', path)
    path = re.sub(r'/clusters/', '/', path)
    path = re.sub(r'/nodePools/', '/', path)
    return path

  def has_default_service_account(self) -> bool:
    sa = self._get_service_account()
    return sa == 'default'

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


class Cluster(models.Resource):
  """Represents a GKE cluster.

  https://cloud.google.com/kubernetes-engine/docs/reference/rest/v1/projects.locations.clusters#Cluster
  """
  _resource_data: dict

  def __init__(self, project_id, resource_data):
    super().__init__(project_id=project_id)
    self._resource_data = resource_data

  @property
  def name(self) -> str:
    return self._resource_data['name']

  @property
  def location(self) -> str:
    return self._resource_data['location']

  @property
  def master_version(self) -> str:
    return self._resource_data['currentMasterVersion']

  @property
  def app_layer_sec_key(self) -> str:
    return self._resource_data['databaseEncryption'].get('keyName')

  def get_full_path(self) -> str:
    if utils.is_region(self._resource_data['location']):
      return (f'projects/{self.project_id}/'
              f'locations/{self.location}/clusters/{self.name}')
    else:
      return (f'projects/{self.project_id}/'
              f'zones/{self.location}/clusters/{self.name}')

  def get_short_path(self) -> str:
    path = self.get_full_path()
    path = re.sub(r'^projects/', '', path)
    path = re.sub(r'/locations/', '/', path)
    path = re.sub(r'/zones/', '/', path)
    path = re.sub(r'/clusters/', '/', path)
    return path

  def has_logging_enabled(self) -> bool:
    return self._resource_data['loggingService'] != 'none'

  def has_monitoring_enabled(self) -> bool:
    return self._resource_data['monitoringService'] != 'none'

  def has_app_layer_enc_enabled(self) -> bool:
    # state := 'DECRYPTED' | 'ENCRYPTED', keyName := 'full_path_to_key_resouce'
    return self._resource_data['databaseEncryption'].get('state') == 'ENCRYPTED'

  @property
  def nodepools(self) -> Iterable[NodePool]:
    nodepools: List[NodePool] = []
    for n in self._resource_data.get('nodePools', []):
      nodepools.append(NodePool(self.project_id, n))
    return nodepools


@functools.lru_cache(maxsize=None)
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
        clusters[c.get_full_path()] = c
    except googleapiclient.errors.HttpError as err:
      errstr = utils.http_error_message(err)
      # TODO(dwes): implement proper exception classes
      raise ValueError(
          f'can\'t list clusters for project {project_id}: {errstr}') from err
  return clusters


@functools.lru_cache(maxsize=None)
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
  return server_config['validMasterVersions']


def get_valid_node_versions(project_id: str, location: str) -> List[str]:
  """Get a list of valid GKE master versions."""
  server_config = _get_server_config(project_id, location)
  return server_config['validNodeVersions']
