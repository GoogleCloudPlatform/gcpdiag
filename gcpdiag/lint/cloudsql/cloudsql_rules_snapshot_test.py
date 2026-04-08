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

from gcpdiag.lint import cloudsql, snapshot_test_base


class TestCloudSql1(snapshot_test_base.RulesSnapshotTestBase):
  rule_pkg = cloudsql
  project_id = 'gcpdiag-cloudsql1-aaaa'

  def _list_rules(self):
    rules = super()._list_rules()
    return [
      r
      for r in rules
      if f'{r.rule_class}_{r.rule_id}'
      not in (
        'BP_2023_002',
        'BP_2026_003',
        'BP_2026_001',
      )
    ]


class TestCloudsql2(snapshot_test_base.RulesSnapshotTestBase):
  rule_pkg = cloudsql
  project_id = 'gcpdiag-cloudsql2-aaaa'

  def _list_rules(self):
    rules = super()._list_rules()
    return [
      r
      for r in rules
      if f'{r.rule_class}_{r.rule_id}'
      in (
        'BP_2023_002',
        'BP_2026_003',
      )
    ]


class TestCloudSql3(snapshot_test_base.RulesSnapshotTestBase):
  rule_pkg = cloudsql
  project_id = 'gcpdiag-cloudsql3-aaaa'

  def _list_rules(self):
    rules = super()._list_rules()
    return [r for r in rules if f'{r.rule_class}_{r.rule_id}' in ('BP_2026_001',)]
