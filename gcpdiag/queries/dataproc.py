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
"""Queries related to Dataproc."""

import re
from typing import Iterable, List, Mapping, Optional

import googleapiclient.errors

from gcpdiag import caching, config, models, utils
from gcpdiag.lint import get_executor
from gcpdiag.queries import apis, crm, gce, network


class Cluster(models.Resource):
  """Represents Dataproc Cluster"""

  name: str
  _resource_data: Mapping

  def __init__(self, name: str, project_id: str, resource_data: Mapping):
    super().__init__(project_id)
    self.name = name
    self._resource_data = resource_data

  def is_running(self) -> bool:
    return self.status == 'RUNNING'

  def get_software_property(self, property_name) -> str:
    return self._resource_data['config']['softwareConfig']['properties'].get(
        property_name)

  def is_stackdriver_logging_enabled(self) -> bool:
    # Unless overridden during create,
    # properties with default values are not returned,
    # therefore get_software_property should only return when its false
    return (not self.get_software_property(
        'dataproc:dataproc.logging.stackdriver.enable') == 'false')

  def is_stackdriver_monitoring_enabled(self) -> bool:
    return (self.get_software_property(
        'dataproc:dataproc.monitoring.stackdriver.enable') == 'true')

  @property
  def region(self) -> str:
    """biggest regions have a trailing '-d' at most in its zoneUri

    https://www.googleapis.com/compute/v1/projects/dataproc1/zones/us-central1-d
    """
    return self._resource_data['config']['gceClusterConfig']['zoneUri'].split(
        '/')[-1][0:-2]

  @property
  def zone(self) -> Optional[str]:
    zone = (self._resource_data.get('config', {}).get('gceClusterConfig',
                                                      {}).get('zoneUri'))
    if zone:
      m = re.search(r'/zones/([^/]+)$', zone)
      if m:
        return m.group(1)
    raise RuntimeError(f"can't determine zone for cluster {self.name}")

  @property
  def full_path(self) -> str:
    return (
        f'projects/{self.project_id}/regions/{self.region}/clusters/{self.name}'
    )

  @property
  def short_path(self) -> str:
    return f'{self.project_id}/{self.region}/{self.name}'

  @property
  def status(self) -> str:
    return self._resource_data['status']['state']

  def __str__(self) -> str:
    return self.short_path

  @property
  def cluster_uuid(self) -> str:
    return self._resource_data['clusterUuid']

  @property
  def image_version(self):
    return self._resource_data['config']['softwareConfig']['imageVersion']

  @property
  def vm_service_account_email(self):
    sa = self._resource_data['config']['gceClusterConfig'].get('serviceAccount')
    if sa is None:
      sa = crm.get_project(self.project_id).default_compute_service_account
    return sa

  @property
  def is_gce_cluster(self) -> bool:
    return bool(self._resource_data.get('config', {}).get('gceClusterConfig'))

  @property
  def gce_network_uri(self) -> Optional[str]:
    """Get network uri from cluster network or subnetwork"""
    if not self.is_gce_cluster:
      raise RuntimeError(
          'Can not return network URI for a Dataproc on GKE cluster')
    network_uri = (self._resource_data.get('config',
                                           {}).get('gceClusterConfig',
                                                   {}).get('networkUri'))
    if not network_uri:
      subnetwork_uri = (self._resource_data.get('config', {}).get(
          'gceClusterConfig', {}).get('subnetworkUri'))
      network_uri = network.get_subnetwork_from_url(subnetwork_uri).network
    return network_uri

  @property
  def gce_subnetwork_uri(self) -> Optional[str]:
    """Get subnetwork uri from cluster subnetwork."""
    if not self.is_gce_cluster:
      raise RuntimeError(
          'Can not return subnetwork URI for a Dataproc on GKE cluster')
    subnetwork_uri = (self._resource_data.get('config',
                                              {}).get('gceClusterConfig',
                                                      {}).get('subnetworkUri'))
    if not subnetwork_uri:
      subnetwork_uri = ('https://www.googleapis.com/compute/v1/projects/' +
                        self.project_id + '/regions/' + self.region +
                        '/subnetworks/default')
    return subnetwork_uri

  @property
  def is_single_node_cluster(self) -> bool:
    workers = (self._resource_data.get('config',
                                       {}).get('workerConfig',
                                               {}).get('numInstances', 0))
    return workers == 0

  @property
  def is_ha_cluster(self) -> bool:
    masters = (self._resource_data.get('config',
                                       {}).get('masterConfig',
                                               {}).get('numInstances', 1))
    return masters != 1

  @property
  def is_internal_ip_only(self) -> bool:
    # internalIpOnly is set to true by default when creating a
    # Dataproc 2.2 image version cluster.
    # The default should be false in older versions instead.
    internal_ip_only = self._resource_data['config']['gceClusterConfig'][
        'internalIpOnly']
    return internal_ip_only


class Region:
  """Represents Dataproc region"""

  project_id: str
  region: str

  def __init__(self, project_id: str, region: str):
    self.project_id = project_id
    self.region = region

  def get_clusters(self, context: models.Context) -> Iterable[Cluster]:
    clusters = []
    for cluster in self.query_api():
      if not context.match_project_resource(resource=cluster.get('clusterName'),
                                            labels=cluster.get('labels', {})):
        continue
      c = Cluster(
          name=cluster['clusterName'],
          project_id=self.project_id,
          resource_data=cluster,
      )
      clusters.append(c)
    return clusters

  def query_api(self) -> Iterable[dict]:
    api = apis.get_api('dataproc', 'v1', self.project_id)
    query = (api.projects().regions().clusters().list(projectId=self.project_id,
                                                      region=self.region))
    # be careful not to retry too many times because querying all regions
    # sometimes causes requests to fail permanently
    resp = query.execute(num_retries=1)
    return resp.get('clusters', [])


class Dataproc:
  """Represents Dataproc product"""

  project_id: str

  def __init__(self, project_id: str):
    self.project_id = project_id

  def get_regions(self) -> Iterable[Region]:
    return [
        Region(self.project_id, r.name)
        for r in gce.get_all_regions(self.project_id)
    ]

  def is_api_enabled(self) -> bool:
    return apis.is_enabled(self.project_id, 'dataproc')


@caching.cached_api_call
def get_clusters(context: models.Context) -> Iterable[Cluster]:
  r: List[Cluster] = []
  dataproc = Dataproc(context.project_id)
  if not dataproc.is_api_enabled():
    return r
  executor = get_executor()
  for clusters in executor.map(lambda r: r.get_clusters(context),
                               dataproc.get_regions()):
    r += clusters
  return r


class AutoScalingPolicy(models.Resource):
  """AutoScalingPolicy."""
  _resource_data: dict

  def __init__(self, project_id, resource_data, region):
    super().__init__(project_id=project_id)
    self._resource_data = resource_data
    self.region = region

  @property
  def policy_id(self) -> str:
    return self._resource_data['id']

  @property
  def full_path(self) -> str:
    return self._resource_data['name']

  @property
  def short_path(self) -> str:
    return f'{self.project_id}/{self.region}/{self.policy_id}'

  @property
  def name(self) -> str:
    return self._resource_data['name']

  @property
  def scale_down_factor(self) -> float:
    return self._resource_data['basicAlgorithm']['yarnConfig'].get(
        'scaleDownFactor', 0.0)


@caching.cached_api_call
def get_auto_scaling_policy(project_id: str, region: str,
                            policy_id: str) -> AutoScalingPolicy:
  # logging.info('fetching autoscalingpolicy: %s', project_id)
  dataproc = apis.get_api('dataproc', 'v1', project_id)
  name = f'projects/{project_id}/regions/{region}/autoscalingPolicies/{policy_id}'
  try:
    request = dataproc.projects().regions().autoscalingPolicies().get(name=name)
    response = request.execute(num_retries=config.API_RETRIES)
    return AutoScalingPolicy(project_id, response, region)
  except googleapiclient.errors.HttpError as err:
    raise utils.GcpApiError(err) from err
