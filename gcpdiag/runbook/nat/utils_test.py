# Copyright 2023 Google LLC
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
"""Test for NAT utils."""

import unittest

from gcpdiag.runbook.nat import utils


class RegionFromZoneTest(unittest.TestCase):
  """Test region_from_zone."""

  def test_region_from_zone(self):
    self.assertEqual(utils.region_from_zone('us-central1-a'), 'us-central1')
    self.assertEqual(utils.region_from_zone('europe-west1-b'), 'europe-west1')
    self.assertEqual(utils.region_from_zone('asia-northeast3-c'),
                     'asia-northeast3')
    self.assertEqual(utils.region_from_zone('us-east4-a'), 'us-east4')

  def test_no_match(self):
    self.assertEqual(utils.region_from_zone('us-central1'), '')
    self.assertEqual(utils.region_from_zone(''), '')
    self.assertEqual(utils.region_from_zone('invalid-zone'), '')
