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

from gcpdiag.lint import lb, snapshot_test_base


class Test(snapshot_test_base.RulesSnapshotTestBase):
  rule_pkg = lb
  project_id = 'gcpdiag-lb1-aaaa'

  def _list_rules(self):
    rules = super()._list_rules()
    return [r for r in rules if not (r.rule_class.value == 'BP' and r.rule_id == '2026_001')]


class TestLb2(snapshot_test_base.RulesSnapshotTestBase):
  rule_pkg = lb
  project_id = 'gcpdiag-lb2-aaaa'

  def _list_rules(self):
    rules = super()._list_rules()
    return [r for r in rules if r.rule_class.value == 'BP' and r.rule_id == '2026_001']
