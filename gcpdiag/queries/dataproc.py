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

import logging
import re
from typing import Iterable, List, Mapping, Optional

import googleapiclient.errors
import requests

from gcpdiag import caching, config, models, utils
from gcpdiag.lint import get_executor
from gcpdiag.queries import apis, crm, gce, network, web


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
  def is_custom_gcs_connector(self) -> bool:
    return bool(
        self._resource_data.get('config', {}).get('gceClusterConfig', {}).get(
            'metadata', {}).get('GCS_CONNECTOR_VERSION'))

  @property
  def cluster_provided_bq_connector(self):
    """Check user-supplied BigQuery connector on the cluster level"""
    bigquery_connector = (self._resource_data.get('config', {}).get(
        'gceClusterConfig', {}).get('metadata',
                                    {}).get('SPARK_BQ_CONNECTOR_VERSION'))
    if not bigquery_connector:
      bigquery_connector = (self._resource_data.get('config', {}).get(
          'gceClusterConfig', {}).get('metadata',
                                      {}).get('SPARK_BQ_CONNECTOR_URL'))
      if bigquery_connector:
        if bigquery_connector == 'spark-bigquery-latest.jar':
          return 'spark-bigquery-latest'
        else:
          match = re.search(
              r'spark-bigquery(?:-with-dependencies_\d+\.\d+)?-(\d+\.\d+\.\d+)\.jar',
              bigquery_connector)
          if match:
            return match.group(1)
      # If returns None, it means that the cluster is using the default,
      # pre-installed BQ connector for the image version
      return bigquery_connector

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

  @property
  def has_autoscaling_policy(self) -> bool:
    """Checks if an autoscaling policy is configured for the cluster."""
    return bool(self._resource_data['config'].get('autoscalingConfig', {}))

  @property
  def autoscaling_policy_id(self) -> str:
    """Returns the autoscaling policy ID for the cluster."""
    if self.has_autoscaling_policy:
      return (self._resource_data['config'].get('autoscalingConfig',
                                                {}).get('policyUri',
                                                        '').split('/')[-1])
    else:
      return ''

  @property
  def number_of_primary_workers(self) -> float:
    """Gets the number of primary worker nodes in the cluster."""
    return (self._resource_data['config'].get('workerConfig',
                                              {}).get('numInstances', 0))

  @property
  def number_of_secondary_workers(self) -> float:
    """Gets the number of secondary worker nodes in the cluster."""
    return (self._resource_data['config'].get('secondaryWorkerConfig',
                                              {}).get('numInstances', 0))

  @property
  def is_preemptible_primary_workers(self) -> bool:
    """Checks if the primary worker nodes in the cluster are preemptible."""
    return (self._resource_data['config'].get('workerConfig',
                                              {}).get('isPreemptible', False))

  @property
  def is_preemptible_secondary_workers(self) -> bool:
    """Checks if the secondary worker nodes in the cluster are preemptible."""
    return (self._resource_data['config'].get('secondaryWorkerConfig',
                                              {}).get('isPreemptible', False))

  @property
  def initialization_actions(self) -> List[str]:
    return self._resource_data['config'].get('initializationActions', [])


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
    try:
      api = apis.get_api('dataproc', 'v1', self.project_id)
      query = (api.projects().regions().clusters().list(
          projectId=self.project_id, region=self.region))
      # be careful not to retry too many times because querying all regions
      # sometimes causes requests to fail permanently
      resp = query.execute(num_retries=1)
      return resp.get('clusters', [])
    except googleapiclient.errors.HttpError as err:
      # b/371526148 investigate permission denied error
      logging.error(err)
      return []
      # raise utils.GcpApiError(err) from err


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


@caching.cached_api_call
def get_cluster(cluster_name, region, project) -> Optional[Cluster]:
  api = apis.get_api('dataproc', 'v1', project)
  request = api.projects().regions().clusters().get(projectId=project,
                                                    clusterName=cluster_name,
                                                    region=region)
  try:
    r = request.execute(num_retries=config.API_RETRIES)
  except googleapiclient.errors.HttpError as err:
    logging.error(err)
    return None
  return Cluster(r['clusterName'], project_id=r['projectId'], resource_data=r)


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

  @property
  def has_graceful_decommission_timeout(self) -> bool:
    """Checks if a graceful decommission timeout is configured in the autoscaling policy."""
    return bool(
        self._resource_data.get('basicAlgorithm',
                                {}).get('yarnConfig',
                                        {}).get('gracefulDecommissionTimeout',
                                                {}))

  @property
  def graceful_decommission_timeout(self) -> float:
    """Gets the configured graceful decommission timeout in the autoscaling policy."""
    return (self._resource_data.get('basicAlgorithm',
                                    {}).get('yarnConfig', {}).get(
                                        'gracefulDecommissionTimeout', -1))


@caching.cached_api_call
def get_auto_scaling_policy(project_id: str, region: str,
                            policy_id: str) -> AutoScalingPolicy:
  # logging.info('fetching autoscalingpolicy: %s', project_id)
  dataproc = apis.get_api('dataproc', 'v1', project_id)
  name = (
      f'projects/{project_id}/regions/{region}/autoscalingPolicies/{policy_id}')
  try:
    request = dataproc.projects().regions().autoscalingPolicies().get(name=name)
    response = request.execute(num_retries=config.API_RETRIES)
    return AutoScalingPolicy(project_id, response, region)
  except googleapiclient.errors.HttpError as err:
    raise utils.GcpApiError(err) from err


@caching.cached_api_call
def list_auto_scaling_policies(project_id: str,
                               region: str) -> List[AutoScalingPolicy]:
  """Lists all autoscaling policies in the given project and region."""
  dataproc = apis.get_api('dataproc', 'v1', project_id)
  parent = f'projects/{project_id}/regions/{region}'
  try:
    request = (dataproc.projects().regions().autoscalingPolicies().list(
        parent=parent))
    response = request.execute(num_retries=config.API_RETRIES)
    return [
        AutoScalingPolicy(project_id, policy_data, region)
        for policy_data in response.get('policies', [])
    ]
  except googleapiclient.errors.HttpError as err:
    raise utils.GcpApiError(err) from err


class Job(models.Resource):
  """Job."""

  _resource_data: dict

  def __init__(self, project_id, job_id, region, resource_data):
    super().__init__(project_id=project_id)
    self._resource_data = resource_data
    self.region = region
    self.job_id = job_id

  @property
  def full_path(self) -> str:
    return (
        f'projects/{self.project_id}/regions/{self.region}/jobs/{self.job_id}')

  @property
  def short_path(self) -> str:
    return f'{self.project_id}/{self.region}/{self.job_id}'

  @property
  def cluster_name(self) -> str:
    return self._resource_data['placement']['clusterName']

  @property
  def cluster_uuid(self) -> str:
    return self._resource_data['placement']['clusterUuid']

  @property
  def state(self):
    return self._resource_data['status']['state']

  @property
  def details(self):
    if self._resource_data['status']['state'] == 'ERROR':
      return self._resource_data['status']['details']
    return None

  @property
  def status_history(self):
    status_history_dict = {}
    for previous_status in self._resource_data['statusHistory']:
      if previous_status['state'] not in status_history_dict:
        status_history_dict[
            previous_status['state']] = previous_status['stateStartTime']

    return status_history_dict

  @property
  def yarn_applications(self):
    return self._resource_data['yarnApplications']

  @property
  def driver_output_resource_uri(self):
    return self._resource_data.get('driverOutputResourceUri')

  @property
  def job_uuid(self):
    return self._resource_data.get('jobUuid')

  @property
  def job_provided_bq_connector(self):
    """Check user-supplied BigQuery connector on the job level"""
    jar_file_uris = (self._resource_data.get('sparkJob', {}).get('jarFileUris'))
    if jar_file_uris is not None:
      for file in jar_file_uris:
        if 'spark-bigquery-latest.jar' in file:
          return 'spark-bigquery-latest'
        else:
          match = re.search(
              r'spark-bigquery(?:-with-dependencies_\d+\.\d+)?-(\d+\.\d+\.\d+)\.jar',
              file)
          if match:
            return match.group(1)
    return None


@caching.cached_api_call
def get_job_by_jobid(project_id: str, region: str, job_id: str):
  dataproc = apis.get_api('dataproc', 'v1', project_id)
  try:
    request = (dataproc.projects().regions().jobs().get(projectId=project_id,
                                                        region=region,
                                                        jobId=job_id))
    response = request.execute(num_retries=config.API_RETRIES)
    return Job(project_id, region, job_id, response)
  except googleapiclient.errors.HttpError as err:
    raise utils.GcpApiError(err) from err


@caching.cached_api_call
def extract_dataproc_supported_version() -> list[str]:
  """Extract the supported Dataproc versions(use Debian as representative).
  """

  page_url = 'https://cloud.google.com/dataproc/docs/concepts/versioning/dataproc-version-clusters'

  try:
    table = web.fetch_and_extract_table(page_url,
                                        tag='h3',
                                        tag_id='debian_images')
    if table:
      rows = table.find_all('tr')[1:]  #Skip the header row
      version_list = []

      for row in rows:
        dp_version = row.find_all('td')[0].get_text().strip().split('-')[0]
        version_list.append(dp_version)
      return version_list

    else:
      return []
  except (
      requests.exceptions.RequestException,
      AttributeError,
      TypeError,
      ValueError,
      IndexError,
  ) as e:
    logging.error(
        'Error in extracting dataproc versions: %s',
        e,
    )
    return []


@caching.cached_api_call
def extract_dataproc_bigquery_version(image_version) -> list[str]:
  """Extract Dataproc BigQuery connector versions based on image version GCP documentation.
  """

  page_url = ('https://cloud.google.com/dataproc/docs/concepts/versioning/'
              'dataproc-release-' + image_version)

  try:
    table = web.fetch_and_extract_table(page_url, tag='div')
    bq_version = []
    if table:
      rows = table.find_all('tr')[1:]
      for row in rows:
        cells = row.find_all('td')
        if 'BigQuery Connector' in cells[0].get_text(strip=True):
          bq_version = cells[1].get_text(strip=True)
    return bq_version
  except (
      requests.exceptions.RequestException,
      AttributeError,
      TypeError,
      ValueError,
      IndexError,
  ) as e:
    logging.error(
        '%s Error in extracting BigQuery connector versions.'
        '  Please check BigQuery Connector version on %s',
        e,
        page_url,
    )
    return []
