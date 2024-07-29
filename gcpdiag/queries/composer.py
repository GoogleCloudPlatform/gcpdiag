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
"""Queries related to Composer."""

import logging
import re
from typing import Iterable, List, Tuple

from boltons.iterutils import get_path
from packaging import version

from gcpdiag import caching, models
from gcpdiag.lint import get_executor
from gcpdiag.queries import apis, crm


class Environment(models.Resource):
  """ Represents Composer environment """
  _resource_data: dict

  def __init__(self, project_id: str, resource_data: dict):
    super().__init__(project_id)
    self._resource_data = resource_data
    self.region, self.name = self.parse_full_path()
    self.version_pattern = re.compile(r'composer-(.*)-airflow-(.*)')

  @property
  def num_schedulers(self) -> int:
    return get_path(self._resource_data,
                    ('config', 'workloadsConfig', 'scheduler', 'count'),
                    default=1)

  @property
  def worker_cpu(self) -> float:
    return get_path(self._resource_data,
                    ('config', 'workloadsConfig', 'worker', 'cpu'))

  @property
  def worker_memory_gb(self) -> float:
    return get_path(self._resource_data,
                    ('config', 'workloadsConfig', 'worker', 'memoryGb'))

  @property
  def worker_max_count(self) -> int:
    return get_path(self._resource_data,
                    ('config', 'workloadsConfig', 'worker', 'maxCount'))

  @property
  def worker_concurrency(self) -> float:

    def default_value():
      airflow_version = self.airflow_version

      if version.parse(airflow_version) < version.parse('2.3.3'):
        return 12 * self.worker_cpu
      else:
        return min(32, 12 * self.worker_cpu, 8 * self.worker_memory_gb)

    return float(
        self.airflow_config_overrides.get('celery-worker_concurrency',
                                          default_value()))

  @property
  def parallelism(self) -> float:
    return float(self.airflow_config_overrides.get('core-parallelism', 'inf'))

  @property
  def composer_version(self) -> str:
    v = self.version_pattern.search(self.image_version)
    assert v is not None
    return v.group(1)

  @property
  def airflow_version(self) -> str:
    v = self.version_pattern.search(self.image_version)
    assert v is not None
    return v.group(2)

  @property
  def is_composer2(self) -> bool:
    return self.composer_version.startswith('2')

  @property
  def full_path(self) -> str:
    return self._resource_data['name']

  @property
  def state(self) -> str:
    return self._resource_data['state']

  @property
  def image_version(self) -> str:
    return self._resource_data['config']['softwareConfig']['imageVersion']

  @property
  def short_path(self) -> str:
    return f'{self.project_id}/{self.region}/{self.name}'

  @property
  def airflow_config_overrides(self) -> dict[str, str]:
    return self._resource_data['config']['softwareConfig'].get(
        'airflowConfigOverrides', {})

  @property
  def network_details(self) -> str:
    nd = self._resource_data['config']['nodeConfig'].get('network')
    if nd is None:
      return (  # Or return a default value, or raise an exception
          'Network not found')
    else:
      return nd

  @property
  def kms_key_name(self) -> str:
    kms = self._resource_data['config']['encryptionConfig'].get('kmsKeyName')
    if kms is None:
      return (  # Or return a default value, or raise an exception
          'No KMS key found')
    else:
      return kms

  @property
  def service_account(self) -> str:
    sa = self._resource_data['config']['nodeConfig'].get('serviceAccount')
    if sa is None:
      # serviceAccount is marked as optional in REST API docs
      # using a default GCE SA as a fallback
      project_nr = crm.get_project(self.project_id).number
      sa = f'{project_nr}-compute@developer.gserviceaccount.com'
    return sa

  def parse_full_path(self) -> Tuple[str, str]:
    match = re.match(r'projects/[^/]*/locations/([^/]*)/environments/([^/]*)',
                     self.full_path)
    if not match:
      raise RuntimeError(f'Can\'t parse full_path {self.full_path}')
    return match.group(1), match.group(2)

  def __str__(self) -> str:
    return self.short_path

  def is_private_ip(self) -> bool:
    return self._resource_data['config']['privateEnvironmentConfig'].get(
        'enablePrivateEnvironment', False)

  @property
  def gke_cluster(self) -> str:
    return self._resource_data['config']['gkeCluster']


COMPOSER_REGIONS = [
    'asia-northeast2', 'us-central1', 'northamerica-northeast1', 'us-west3',
    'southamerica-east1', 'us-east1', 'asia-northeast1', 'europe-west1',
    'europe-west2', 'asia-northeast3', 'us-west4', 'asia-east2',
    'europe-central2', 'europe-west6', 'us-west2', 'australia-southeast1',
    'europe-west3', 'asia-south1', 'us-west1', 'us-east4', 'asia-southeast1'
]


def _query_region_envs(region, api, project_id):
  query = api.projects().locations().environments().list(
      parent=f'projects/{project_id}/locations/{region}')
  # be careful not to retry too many times because querying all regions
  # sometimes causes requests to fail permanently
  resp = query.execute(num_retries=1)
  return resp.get('environments', [])


def _query_regions_envs(regions, api, project_id):
  result: List[Environment] = []
  executor = get_executor()
  for descriptions in executor.map(
      lambda r: _query_region_envs(r, api, project_id), regions):
    result += descriptions
  return result


@caching.cached_api_call
def get_environments(context: models.Context) -> Iterable[Environment]:
  environments: List[Environment] = []
  if not apis.is_enabled(context.project_id, 'composer'):
    return environments
  api = apis.get_api('composer', 'v1', context.project_id)

  for env in _query_regions_envs(COMPOSER_REGIONS, api, context.project_id):
    # projects/{projectId}/locations/{locationId}/environments/{environmentId}.
    result = re.match(r'projects/[^/]+/locations/([^/]+)/environments/([^/]+)',
                      env['name'])
    if not result:
      logging.error('invalid composer name: %s', env['name'])
      continue
    location = result.group(1)
    labels = env.get('labels', {})
    name = result.group(2)
    if not context.match_project_resource(
        location=location, labels=labels, resource=name):
      continue

    environments.append(Environment(context.project_id, env))
  return environments
