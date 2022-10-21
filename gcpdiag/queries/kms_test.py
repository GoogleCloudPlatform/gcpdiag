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

from gcpdiag.queries import apis_stub, kms

DUMMY_PROJECT_NAME = 'gcpdiag-gke1-aaaa'
BASE_KEY_NAME = f'projects/{DUMMY_PROJECT_NAME}/locations/us-central1/keyRings/usckr/cryptoKeys/'
DUMMY_DESTROYED_CRYPTO_KEY_NAME = BASE_KEY_NAME + 'kms-key-destroyed'
DUMMY_DISABLED_CRYPTO_KEY_NAME = BASE_KEY_NAME + 'kms-key-disabled'
DUMMY_ENABLED_CRYPTO_KEY_NAME = BASE_KEY_NAME + 'kms-key-enabled'

DUMMY_IAM_POLICY_PROJECT_NAME = 'gcpdiag-apigee1-aaaa'
DUMMY_IAM_POLICY_CRYPTO_KEY_NAME = f'projects/{DUMMY_IAM_POLICY_PROJECT_NAME}/locations/us-central1/keyRings/apigee-keyring/cryptoKeys/apigee-key'  # pylint: disable=C0301
DUMMY_IAM_POLICY_MEMBER = 'serviceAccount:service-12340005@gcp-sa-apigee.iam.gserviceaccount.com'
DUMMY_IAM_POLICY_ROLE = 'roles/cloudkms.cryptoKeyEncrypterDecrypter'


@mock.patch('gcpdiag.queries.apis.get_api', new=apis_stub.get_api_stub)
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

  def test_get_crypto_key_iam_policy(self):
    policy = kms.get_crypto_key_iam_policy(DUMMY_IAM_POLICY_CRYPTO_KEY_NAME)
    assert policy.has_role_permissions(DUMMY_IAM_POLICY_MEMBER,
                                       DUMMY_IAM_POLICY_ROLE)
