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
"""Test logic for GKE Version Support matching"""

from datetime import date
from unittest import mock

from gcpdiag.lint.gke import err_2026_001_gke_version_support
from gcpdiag.utils import Version

MOCK_SCHEDULE = {
  '1.28': {
    'eol': date(2025, 2, 4),
    'extended_eol': date(2026, 1, 9),
  },
  '1.29': {
    'eol': date(2025, 4, 12),
    'extended_eol': date(2026, 1, 25),
  },
  '1.30': {
    'eol': date(2025, 9, 30),
    'extended_eol': date(2026, 7, 30),
  },
}


class TestGkeVersionSupport:
  """Unit tests simulating various combinations for GKE version support logic."""

  project_id = 'gcpdiag-gke1-aaaa'

  def run_simulation(self, version_str, channel, mock_today, expected_unsupported):
    """Helper method to run a simulation against a frozen date."""
    v = Version(version_str)

    # Patch date.today() to our simulated timeline
    with mock.patch('gcpdiag.lint.gke.err_2026_001_gke_version_support.date') as mock_date:
      mock_date.today.return_value = mock_today
      mock_date.side_effect = lambda *args, **kw: date(*args, **kw)

      result = err_2026_001_gke_version_support._is_version_unsupported(v, channel, MOCK_SCHEDULE)

      assert result is expected_unsupported, (
        f'Test Failed! \n'
        f'Version: {version_str}\n'
        f'Channel: {channel}\n'
        f'Date Simulated: {mock_today}\n'
        f'Expected Unsupported?: {expected_unsupported}\n'
        f'Actual Result: {result}'
      )

  def test_stable_channel_past_standard_eol(self):
    # Simulated date: May 1st, 2025.
    # 1.28 EOL was Feb 2025. It should be unsupported.
    self.run_simulation('1.28.3', 'STABLE', date(2025, 5, 1), True)

  def test_extended_channel_past_standard_eol(self):
    # Simulated date: May 1st, 2025.
    # 1.28 EOL was Feb 2025, BUT extended EOL is Jan 2026. It SHOULD be supported.
    self.run_simulation('1.28.3', 'EXTENDED', date(2025, 5, 1), False)

  def test_extended_channel_past_extended_eol(self):
    # Simulated date: Feb 1st, 2026.
    # 1.28 Extended EOL was Jan 9, 2026. It should be unsupported now.
    self.run_simulation('1.28.5', 'EXTENDED', date(2026, 2, 1), True)

  def test_rapid_channel_future_date(self):
    # Simulated date: March 1st, 2025.
    # 1.29 EOL is April 2025. It is still supported.
    self.run_simulation('1.29.1', 'RAPID', date(2025, 3, 1), False)

  def test_unspecified_fallback_channel(self):
    # Simulated date: May 1st, 2025.
    # If a cluster doesn't specify a channel, it uses standard EOL. 1.28 should fail.
    self.run_simulation('1.28.2', 'UNSPECIFIED', date(2025, 5, 1), True)

  def test_too_old_version(self):
    # 1.15 is not even in the MOCK_SCHEDULE, meaning it's so old it rolled off.
    # Should always be flagged as unsupported.
    self.run_simulation('1.15.10', 'STABLE', date(2024, 1, 1), True)

  def test_brand_new_version(self):
    # 1.34 is newer than the array. It's technically active/under active development.
    # We should default to supported (False).
    self.run_simulation('1.34.1', 'RAPID', date(2025, 1, 1), False)
