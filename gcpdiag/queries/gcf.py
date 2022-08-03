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
"""Queries related to GCP CloudFunctions instances."""

import logging
import re
from typing import Dict, Mapping

import googleapiclient.errors

from gcpdiag import caching, config, models, utils
from gcpdiag.queries import apis


class CloudFunction(models.Resource):
  """Represents a GCF instance."""
  _resource_data: dict

  def __init__(self, project_id, resource_data):
    super().__init__(project_id=project_id)
    self._resource_data = resource_data
    self._metadata_dict = None

  @property
  def name(self) -> str:
    m = re.search(r'/functions/([^/]+)$', self._resource_data['name'])
    if not m:
      raise RuntimeError('can\'t determine name of cloudfunction %s' %
                         (self._resource_data['name']))
    return m.group(1)

  @property
  def description(self) -> str:
    return self._resource_data['description']

  @property
  def full_path(self) -> str:
    return self._resource_data['name']

  @property
  def short_path(self) -> str:
    path = self.project_id + '/' + self.name
    return path

  @property
  def runtime(self) -> str:
    return self._resource_data['runtime']

  @property
  def memory(self) -> str:
    return self._resource_data['availableMemoryMb']


@caching.cached_api_call
def get_cloudfunctions(context: models.Context) -> Mapping[str, CloudFunction]:
  """Get a list of CloudFunctions matching the given context, indexed by CloudFunction name."""
  cloudfunctions: Dict[str, CloudFunction] = {}
  if not apis.is_enabled(context.project_id, 'cloudfunctions'):
    return cloudfunctions
  gcf_api = apis.get_api('cloudfunctions', 'v1', context.project_id)
  logging.info('fetching list of GCF functions in project %s',
               context.project_id)
  query = gcf_api.projects().locations().functions().list(
      parent=f'projects/{context.project_id}/locations/-')
  try:
    resp = query.execute(num_retries=config.API_RETRIES)
    if 'functions' not in resp:
      return cloudfunctions
    for resp_f in resp['functions']:
      # verify that we have some minimal data that we expect
      if 'name' not in resp_f or 'runtime' not in resp_f:
        raise RuntimeError(
            'missing data in projects.locations.functions.list response')
      f = CloudFunction(project_id=context.project_id, resource_data=resp_f)
      cloudfunctions[f.full_path] = f
  except googleapiclient.errors.HttpError as err:
    raise utils.GcpApiError(err) from err
  return cloudfunctions
