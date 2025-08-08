# Copyright 2025 Google LLC
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
"""Unit tests for validating custom datatypes."""

import unittest

from gcpdiag.queries.iam import (DEFAULT_SERVICE_ACCOUNT_DOMAINS,
                                 SERVICE_AGENT_DOMAINS)
from gcpdiag.types import Email  # Import the Email class

REGULAR_EMAIL = ('example.com', 'example.com.gh', 'example.engineer')


class TestServiceAccountDomains(unittest.TestCase):
  """Unit tests for validating service account and regular email domains.

  This test suite ensures that:
  - Service account domains from DEFAULT_SERVICE_ACCOUNT_DOMAINS and
    SERVICE_AGENT_DOMAINS can form valid email addresses.
  - Regular email domains also form valid email addresses.
  """

  def test_default_service_account_domains(self):
    """Test that emails formed with DEFAULT_SERVICE_ACCOUNT_DOMAINS are valid."""
    for domain in DEFAULT_SERVICE_ACCOUNT_DOMAINS:
      email = f'test@{domain}'
      self.assertTrue(Email.is_valid(email), f"Email '{email}' is not valid")

  def test_service_agent_domains(self):
    """Test that emails formed with SERVICE_AGENT_DOMAINS are valid."""
    for domain in SERVICE_AGENT_DOMAINS:
      email = f'test@{domain}'
      self.assertTrue(Email.is_valid(email), f"Email '{email}' is not valid")

  def test_regular_email(self):
    """Test that emails formed with REGULAR_EMAIL domains are valid."""
    for domain in REGULAR_EMAIL:
      email = f'test@{domain}'
      self.assertTrue(Email.is_valid(email), f"Email '{email}' is not valid")
