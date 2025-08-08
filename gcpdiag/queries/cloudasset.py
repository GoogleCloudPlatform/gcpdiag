# Copyright 2024 Google LLC
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
"""Queries related to GCP Cloud Asset Inventory."""

import logging
import re
from typing import Dict, Mapping, Optional

import googleapiclient.errors

from gcpdiag import caching, config, models, utils
from gcpdiag.queries import apis


class AssetResource(models.Resource):
  """Represents Resource Retrieved from the Cloud Asset Inventory."""
  _resource_data: dict

  def __init__(self, project_id, resource_data):
    super().__init__(project_id=project_id)
    self._resource_data = resource_data

  @property
  def name(self) -> str:
    m = re.search(r'//(.+)', self._resource_data['name'])
    if not m:
      raise RuntimeError('can\'t determine name of service %s' %
                         (self._resource_data['name']))
    return m.group(1)

  @property
  def full_path(self) -> str:
    return self.name

  @property
  def asset_type(self) -> str:
    return self._resource_data['assetType']


@caching.cached_api_call
def search_all_resources(
    project_id: str,
    asset_type: Optional[str] = None,
    query: Optional[str] = None,
) -> Mapping[str, AssetResource]:
  """Searches all resources in the project."""
  resources: Dict[str, AssetResource] = {}

  if not apis.is_enabled(project_id, 'cloudasset'):
    return resources
  cloudasset_api = apis.get_api('cloudasset', 'v1', project_id)
  logging.debug('fetching list of resources in the project %s', project_id)
  request = cloudasset_api.v1().searchAllResources(
      scope=f'projects/{project_id}', assetTypes=asset_type, query=query)
  response = request.execute(num_retries=config.API_RETRIES)
  try:
    if 'results' in response:
      for resource in response['results']:
        resources[resource['name']] = AssetResource(project_id, resource)
  except googleapiclient.errors.HttpError as err:
    raise utils.GcpApiError(err) from err
  return resources
