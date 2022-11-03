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
"""Queries related to GCP Cloud Key Management."""

import logging

import googleapiclient.errors

from gcpdiag import caching, config, models, utils
from gcpdiag.queries import apis, iam
from gcpdiag.utils import GcpApiError


class CryptoKey(models.Resource):
  """Represents a KMS Crypto Key.

  See also the API documentation:
  https://cloud.google.com/kms/docs/reference/rest/v1/projects.locations.keyRings.cryptoKeys
  """

  @property
  def full_path(self) -> str:
    return self._resource_data['name']

  @property
  def name(self) -> str:
    return self._resource_data['name']

  def is_destroyed(self) -> bool:
    return self._resource_data['primary'].get('state') == 'DESTROYED'

  def is_enabled(self) -> bool:
    return self._resource_data['primary'].get('state') == 'ENABLED'

  def __init__(self, project_id, resource_data):
    super().__init__(project_id=project_id)
    self._resource_data = resource_data


class KMSCryptoKeyIAMPolicy(iam.BaseIAMPolicy):

  def _is_resource_permission(self, permission):
    return True


@caching.cached_api_call
def get_crypto_key(key_name: str) -> CryptoKey:
  """Get a Crypto Key object by its resource name, caching the result."""

  project_id = utils.get_project_by_res_name(key_name)
  kms_api = apis.get_api('cloudkms', 'v1', project_id)
  query = kms_api.projects().locations().keyRings().cryptoKeys().get(
      name=key_name)
  logging.info('fetching KMS Key %s in project %s',
               utils.extract_value_from_res_name(key_name, 'cryptoKeys'),
               project_id)
  try:
    resource_data = query.execute(num_retries=config.API_RETRIES)
  except googleapiclient.errors.HttpError as err:
    raise GcpApiError(err) from err
  return CryptoKey(project_id, resource_data)


@caching.cached_api_call
def get_crypto_key_iam_policy(key_name: str) -> KMSCryptoKeyIAMPolicy:

  project_id = utils.get_project_by_res_name(key_name)
  kms_api = apis.get_api('cloudkms', 'v1', project_id)

  query = kms_api.projects().locations().keyRings().cryptoKeys().getIamPolicy(
      resource=key_name)
  return iam.fetch_iam_policy(query, KMSCryptoKeyIAMPolicy, project_id,
                              key_name)
