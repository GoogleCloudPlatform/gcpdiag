# Lint as: python3
"""Queries related to GCP Cloud Key Management."""

import functools
import logging

import googleapiclient.errors

from gcp_doctor import config, models, utils
from gcp_doctor.queries import apis
from gcp_doctor.utils import GcpApiError


class CryptoKey(models.Resource):
  """Represents a KMS Crypto Key.

  See also the API documentation:
  https://cloud.google.com/kms/docs/reference/rest/v1/projects.locations.keyRings.cryptoKeys
  """

  def get_full_path(self) -> str:
    return self._resource_data['name']

  @property
  def name(self) -> str:
    return self._resource_data['name']

  def is_destroyed(self) -> bool:
    return self._resource_data['primary'].get('state') == 'DESTROYED'

  def is_enabled(self) -> bool:
    return self._resource_data['primary'].get('state') == 'ENABLED'

  def __init__(self, key_name):
    project_id = utils.get_project_by_res_name(key_name)
    super().__init__(project_id=project_id)

    kms_api = apis.get_api('cloudkms', 'v1')
    query = kms_api.projects().locations().keyRings().cryptoKeys().get(
        name=key_name)
    logging.info('fetching KMS Key %s in project %s',
                 utils.extract_value_from_res_name(key_name, 'cryptoKeys'),
                 project_id)

    try:
      resource_data = query.execute(num_retries=config.API_RETRIES)
    except googleapiclient.errors.HttpError as err:
      raise GcpApiError(err) from err

    self._resource_data = resource_data


@functools.lru_cache(maxsize=None)
def get_crypto_key(key_name: str) -> CryptoKey:
  """Get a Crypto Key object by its resource name, caching the result."""
  return CryptoKey(key_name)
