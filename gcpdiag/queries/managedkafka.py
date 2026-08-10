# Copyright 2026 Google LLC
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
"""Queries related to GCP Managed Service for Apache Kafka."""

import logging
from typing import Dict, List, Optional

import googleapiclient.errors

from gcpdiag import caching, config, models, utils
from gcpdiag.queries import apis, apis_utils


class Cluster(models.Resource):
  """Represents a Managed Service for Apache Kafka Cluster."""

  def __init__(self, project_id: str, resource_data: dict):
    super().__init__(project_id=project_id)
    self._resource_data = resource_data

  @property
  def name(self) -> str:
    return self._resource_data.get('name', '').split('/')[-1]

  @property
  def full_path(self) -> str:
    return self._resource_data.get('name', '')

  @property
  def short_path(self) -> str:
    return '/'.join(self.full_path.split('/')[-4:])

  @property
  def state(self) -> str:
    return self._resource_data.get('state', 'STATE_UNSPECIFIED')

  @property
  def location(self) -> str:
    return self.full_path.split('/')[3] if len(self.full_path.split('/')) > 3 else ''

  @property
  def broker_details(self) -> List[dict]:
    """Returns details of each broker in the cluster (only populated in FULL view)."""
    return self._resource_data.get('brokerDetails', [])


class Topic(models.Resource):
  """Represents a Managed Service for Apache Kafka Topic."""

  def __init__(self, project_id: str, resource_data: dict):
    super().__init__(project_id=project_id)
    self._resource_data = resource_data

  @property
  def name(self) -> str:
    return self._resource_data.get('name', '').split('/')[-1]

  @property
  def full_path(self) -> str:
    return self._resource_data.get('name', '')

  @property
  def short_path(self) -> str:
    # projects/{project_id}/locations/{location_id}/clusters/{cluster_id}/topics/{topic_id}
    return '/'.join(self.full_path.split('/')[-6:])

  @property
  def partition_count(self) -> int:
    return int(self._resource_data.get('partitionCount', 0))

  @property
  def replication_factor(self) -> int:
    return int(self._resource_data.get('replicationFactor', 0))

  @property
  def configs(self) -> Dict[str, str]:
    return self._resource_data.get('configs', {})

  @property
  def is_internal(self) -> bool:
    """Returns True if the topic is a system/internal topic."""
    return self.name.startswith('__')


class ConsumerGroup(models.Resource):
  """Represents a Managed Service for Apache Kafka Consumer Group."""

  def __init__(self, project_id: str, resource_data: dict):
    super().__init__(project_id=project_id)
    self._resource_data = resource_data

  @property
  def name(self) -> str:
    return self._resource_data.get('name', '').split('/')[-1]

  @property
  def full_path(self) -> str:
    return self._resource_data.get('name', '')

  @property
  def short_path(self) -> str:
    # projects/{project_id}/locations/{location_id}/clusters/{cluster_id}/consumerGroups/{group_id}
    return '/'.join(self.full_path.split('/')[-6:])

  @property
  def state(self) -> str:
    return self._resource_data.get('state', 'STATE_UNSPECIFIED')


class Acl(models.Resource):
  """Represents a Managed Service for Apache Kafka ACL."""

  def __init__(self, project_id: str, resource_data: dict):
    super().__init__(project_id=project_id)
    self._resource_data = resource_data

  @property
  def name(self) -> str:
    full = self._resource_data.get('name', '')
    return full.split('/acls/')[-1] if '/acls/' in full else full.split('/')[-1]

  @property
  def full_path(self) -> str:
    return self._resource_data.get('name', '')

  @property
  def short_path(self) -> str:
    # projects/{project_id}/locations/{location_id}/clusters/{cluster_id}/acls/{acl_id}
    return '/'.join(self.full_path.split('/')[-6:])

  @property
  def acl_entries(self) -> List[dict]:
    return self._resource_data.get('aclEntries', [])


def _get_locations_to_scan(context: models.Context, kafka_api) -> List[str]:
  """Returns a list of locations to scan based on the context."""
  try:
    request = kafka_api.projects().locations().list(name=f'projects/{context.project_id}')
    locations = [
      loc['locationId']
      for loc in apis_utils.list_all(
        request=request,
        next_function=kafka_api.projects().locations().list_next,
        response_keyword='locations',
      )
    ]
    if context.locations_pattern:
      return [loc for loc in locations if context.locations_pattern.match(loc)]
    return locations
  except utils.GcpApiError as err:
    logging.warning(
      'Could not list locations for Managed Kafka in project %s: %s', context.project_id, err
    )
    return []


def _resolve_cluster_path(
  context: models.Context, cluster_name: str, location: Optional[str] = None
) -> str:
  """Constructs or validates the cluster full path."""
  if cluster_name.startswith('projects/'):
    return cluster_name
  if location:
    return f'projects/{context.project_id}/locations/{location}/clusters/{cluster_name}'
  raise ValueError(
    f'cluster_name "{cluster_name}" must be a full resource path '
    '(projects/...) or location must be provided.'
  )


@caching.cached_api_call
def get_clusters(context: models.Context) -> Dict[str, Cluster]:
  """Get a list of Kafka Clusters from the given GCP project."""
  clusters: Dict[str, Cluster] = {}
  if not apis.is_enabled(context.project_id, 'managedkafka'):
    return clusters
  kafka_api = apis.get_api('managedkafka', 'v1', context.project_id)
  locations_to_scan = _get_locations_to_scan(context, kafka_api)
  for loc_id in locations_to_scan:
    try:
      parent_path = f'projects/{context.project_id}/locations/{loc_id}'
      request = kafka_api.projects().locations().clusters().list(parent=parent_path)
      for c in apis_utils.list_all(
        request=request,
        next_function=kafka_api.projects().locations().clusters().list_next,
        response_keyword='clusters',
      ):
        if not context.match_project_resource(resource=c.get('name', '')):
          continue
        cluster = Cluster(project_id=context.project_id, resource_data=c)
        clusters[cluster.full_path] = cluster
    except utils.GcpApiError as err:
      logging.warning('Could not list Kafka clusters for location %s: %s', loc_id, err)
      continue
  return clusters


@caching.cached_api_call
def get_cluster(project_id: str, location: str, cluster_name: str) -> Optional[Cluster]:
  """Retrieve a single Managed Kafka cluster by name and location with full details."""
  if not apis.is_enabled(project_id, 'managedkafka'):
    return None
  kafka_api = apis.get_api('managedkafka', 'v1', project_id)
  logging.debug('Fetching Managed Kafka cluster: %s', cluster_name)
  request = (
    kafka_api.projects()
    .locations()
    .clusters()
    .get(
      name=f'projects/{project_id}/locations/{location}/clusters/{cluster_name}',
      view='CLUSTER_VIEW_FULL',
    )
  )
  try:
    resp = request.execute(num_retries=config.API_RETRIES)
    return Cluster(project_id=project_id, resource_data=resp)
  except googleapiclient.errors.HttpError as err:
    if err.resp.status == 404:
      return None
    raise utils.GcpApiError(err) from err


@caching.cached_api_call
def get_topics(
  context: models.Context, cluster_name: str, location: Optional[str] = None
) -> Dict[str, Topic]:
  """Get Kafka Topics for a specific cluster."""
  topics: Dict[str, Topic] = {}
  if not apis.is_enabled(context.project_id, 'managedkafka'):
    return topics

  kafka_api = apis.get_api('managedkafka', 'v1', context.project_id)
  parent_path = _resolve_cluster_path(context, cluster_name, location)

  try:
    request = kafka_api.projects().locations().clusters().topics().list(parent=parent_path)
    for t in apis_utils.list_all(
      request=request,
      next_function=kafka_api.projects().locations().clusters().topics().list_next,
      response_keyword='topics',
    ):
      if not context.match_project_resource(resource=t.get('name', '')):
        continue
      topic = Topic(project_id=context.project_id, resource_data=t)
      topics[topic.full_path] = topic
  except utils.GcpApiError as err:
    logging.warning('Could not list Kafka topics for cluster %s: %s', cluster_name, err)
  return topics


@caching.cached_api_call
def get_topic(
  project_id: str, location: str, cluster_name: str, topic_name: str
) -> Optional[Topic]:
  """Retrieve a single Managed Kafka topic by name."""
  if not apis.is_enabled(project_id, 'managedkafka'):
    return None
  kafka_api = apis.get_api('managedkafka', 'v1', project_id)
  request = (
    kafka_api.projects()
    .locations()
    .clusters()
    .topics()
    .get(
      name=f'projects/{project_id}/locations/{location}/clusters/{cluster_name}/topics/{topic_name}'
    )
  )
  try:
    resp = request.execute(num_retries=config.API_RETRIES)
    return Topic(project_id=project_id, resource_data=resp)
  except googleapiclient.errors.HttpError as err:
    if err.resp.status == 404:
      return None
    raise utils.GcpApiError(err) from err


@caching.cached_api_call
def get_consumer_groups(
  context: models.Context, cluster_name: str, location: Optional[str] = None
) -> Dict[str, ConsumerGroup]:
  """Get Kafka Consumer Groups for a specific cluster."""
  groups: Dict[str, ConsumerGroup] = {}
  if not apis.is_enabled(context.project_id, 'managedkafka'):
    return groups

  kafka_api = apis.get_api('managedkafka', 'v1', context.project_id)
  parent_path = _resolve_cluster_path(context, cluster_name, location)

  try:
    request = kafka_api.projects().locations().clusters().consumerGroups().list(parent=parent_path)
    for g in apis_utils.list_all(
      request=request,
      next_function=kafka_api.projects().locations().clusters().consumerGroups().list_next,
      response_keyword='consumerGroups',
    ):
      if not context.match_project_resource(resource=g.get('name', '')):
        continue
      group = ConsumerGroup(project_id=context.project_id, resource_data=g)
      groups[group.full_path] = group
  except utils.GcpApiError as err:
    logging.warning('Could not list Kafka consumer groups for cluster %s: %s', cluster_name, err)
  return groups


@caching.cached_api_call
def get_consumer_group(
  project_id: str, location: str, cluster_name: str, group_name: str
) -> Optional[ConsumerGroup]:
  """Retrieve a single Managed Kafka consumer group by name."""
  if not apis.is_enabled(project_id, 'managedkafka'):
    return None
  kafka_api = apis.get_api('managedkafka', 'v1', project_id)
  request = (
    kafka_api.projects()
    .locations()
    .clusters()
    .consumerGroups()
    .get(
      name=f'projects/{project_id}/locations/{location}/clusters/{cluster_name}/consumerGroups/{group_name}'
    )
  )
  try:
    resp = request.execute(num_retries=config.API_RETRIES)
    return ConsumerGroup(project_id=project_id, resource_data=resp)
  except googleapiclient.errors.HttpError as err:
    if err.resp.status == 404:
      return None
    raise utils.GcpApiError(err) from err


@caching.cached_api_call
def get_acls(
  context: models.Context, cluster_name: str, location: Optional[str] = None
) -> Dict[str, Acl]:
  """Get Kafka ACLs for a specific cluster."""
  acls: Dict[str, Acl] = {}
  if not apis.is_enabled(context.project_id, 'managedkafka'):
    return acls

  kafka_api = apis.get_api('managedkafka', 'v1', context.project_id)
  parent_path = _resolve_cluster_path(context, cluster_name, location)

  try:
    request = kafka_api.projects().locations().clusters().acls().list(parent=parent_path)
    for a in apis_utils.list_all(
      request=request,
      next_function=kafka_api.projects().locations().clusters().acls().list_next,
      response_keyword='acls',
    ):
      if not context.match_project_resource(resource=a.get('name', '')):
        continue
      acl = Acl(project_id=context.project_id, resource_data=a)
      acls[acl.full_path] = acl
  except utils.GcpApiError as err:
    logging.warning('Could not list Kafka ACLs for cluster %s: %s', cluster_name, err)
  return acls


@caching.cached_api_call
def get_acl(project_id: str, location: str, cluster_name: str, acl_name: str) -> Optional[Acl]:
  """Retrieve a single Managed Kafka ACL by name."""
  if not apis.is_enabled(project_id, 'managedkafka'):
    return None
  kafka_api = apis.get_api('managedkafka', 'v1', project_id)
  request = (
    kafka_api.projects()
    .locations()
    .clusters()
    .acls()
    .get(name=f'projects/{project_id}/locations/{location}/clusters/{cluster_name}/acls/{acl_name}')
  )
  try:
    resp = request.execute(num_retries=config.API_RETRIES)
    return Acl(project_id=project_id, resource_data=resp)
  except googleapiclient.errors.HttpError as err:
    if err.resp.status == 404:
      return None
    raise utils.GcpApiError(err) from err
