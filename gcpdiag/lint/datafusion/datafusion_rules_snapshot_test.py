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

from unittest import mock

from gcpdiag.lint import datafusion, snapshot_test_base
from gcpdiag.queries import datafusion_test


@mock.patch(
    'gcpdiag.queries.datafusion.extract_support_datafusion_version',
    new=lambda: datafusion_test.SUPPORTED_VERSIONS_DICT,
)
class Test(snapshot_test_base.RulesSnapshotTestBase):
  rule_pkg = datafusion
  project_id = 'gcpdiag-datafusion1-aaaa'
