# Copyright 2022 Google LLC
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
"""Generalize rule snapshot testing"""

import datetime
from unittest import mock

from gcpdiag.lint import gke, snapshot_test_base


class MockDate(datetime.date):
  @classmethod
  def today(cls):
    return datetime.date(2026, 6, 1)


@mock.patch('gcpdiag.lint.gke.err_2026_001_gke_version_support.date', new=MockDate)
class Test(snapshot_test_base.RulesSnapshotTestBase):
  rule_pkg = gke
  project_id = 'gcpdiag-gke1-aaaa'
