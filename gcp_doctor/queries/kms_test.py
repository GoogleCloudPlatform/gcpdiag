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
"""Test code in kms.py."""

from unittest import mock

from gcp_doctor.queries import kms, kms_stub

BASE_KEY_NAME = 'projects/testproject/locations/us-central1/keyRings/usckr/cryptoKeys/'
DUMMY_DESTROYED_CRYPTO_KEY_NAME = BASE_KEY_NAME + 'kms-key-destroyed'
DUMMY_DISABLED_CRYPTO_KEY_NAME = BASE_KEY_NAME + 'kms-key-disabled'
DUMMY_ENABLED_CRYPTO_KEY_NAME = BASE_KEY_NAME + 'kms-key-enabled'


@mock.patch('gcp_doctor.queries.apis.get_api', new=kms_stub.get_api_stub)
class TestCryptoKey:
  """Test kms.CryptoKey."""

  def test_get_crypto_key(self):
    """get_crypto_key returns the right key matched by name."""
    crypto_key = kms.get_crypto_key(DUMMY_ENABLED_CRYPTO_KEY_NAME)
    assert crypto_key.name == DUMMY_ENABLED_CRYPTO_KEY_NAME
    crypto_key = kms.get_crypto_key(DUMMY_DISABLED_CRYPTO_KEY_NAME)
    assert crypto_key.name == DUMMY_DISABLED_CRYPTO_KEY_NAME

  def test_is_destroyed(self):
    crypto_key = kms.get_crypto_key(DUMMY_DESTROYED_CRYPTO_KEY_NAME)
    assert crypto_key.is_destroyed()

  def test_is_enabled(self):
    crypto_key = kms.get_crypto_key(DUMMY_ENABLED_CRYPTO_KEY_NAME)
    assert crypto_key.is_enabled()
    crypto_key = kms.get_crypto_key(DUMMY_DISABLED_CRYPTO_KEY_NAME)
    assert not crypto_key.is_enabled()
