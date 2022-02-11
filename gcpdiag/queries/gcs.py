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
"""Queries related to GCP Cloud Storage

"""

import logging
import re
from typing import Dict, Mapping

import googleapiclient.errors

from gcpdiag import caching, config, models, utils
from gcpdiag.queries import apis, iam


class Bucket(models.Resource):
  """Represents a GCS Bucket."""
  _resource_data: dict

  def __init__(self, project_id, resource_data):
    super().__init__(project_id=project_id)
    self._resource_data = resource_data
    self._metadata_dict = None

  @property
  def id(self) -> str:
    return self._resource_data['id']

  @property
  def name(self) -> str:
    return self._resource_data['name']

  def is_uniform_access(self) -> bool:
    return self._resource_data['iamConfiguration']['uniformBucketLevelAccess'][
        'enabled']

  @property
  def full_path(self) -> str:
    result = re.match(r'https://www.googleapis.com/storage/v1/(.*)',
                      self._resource_data['selfLink'])
    if result:
      return result.group(1)
    else:
      return '>> ' + self._resource_data['selfLink']

  @property
  def short_path(self) -> str:
    path = self.project_id + '/' + self.name
    return path

  @property
  def labels(self) -> dict:
    return self._resource_data.get('labels', {})


class BucketIAMPolicy(iam.BaseIAMPolicy):

  def _is_resource_permission(self, permission):
    return True


@caching.cached_api_call(in_memory=True)
def get_bucket_iam_policy(project_id: str, bucket: str) -> BucketIAMPolicy:
  gcs_api = apis.get_api('storage', 'v1', project_id)
  request = gcs_api.buckets().getIamPolicy(bucket=bucket)

  return iam.fetch_iam_policy(request, BucketIAMPolicy, project_id, bucket)


@caching.cached_api_call(in_memory=True)
def get_buckets(context: models.Context) -> Mapping[str, Bucket]:

  buckets: Dict[str, Bucket] = {}
  if not apis.is_enabled(context.project_id, 'storage'):
    return buckets
  gcs_api = apis.get_api('storage', 'v1', context.project_id)
  logging.info('fetching list of GCS buckets in project %s', context.project_id)
  query = gcs_api.buckets().list(project=context.project_id)
  try:
    resp = query.execute(num_retries=config.API_RETRIES)
    if 'items' not in resp:
      return buckets
    for resp_b in resp['items']:
      # verify that we have some minimal data that we expect
      if 'id' not in resp_b:
        raise RuntimeError('missing data in bucket response')
      f = Bucket(project_id=context.project_id, resource_data=resp_b)
      buckets[f.full_path] = f
  except googleapiclient.errors.HttpError as err:
    raise utils.GcpApiError(err) from err
  return buckets
