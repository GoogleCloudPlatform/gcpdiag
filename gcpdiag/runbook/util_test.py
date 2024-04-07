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
"""Contains Util related Tests"""
import unittest
from datetime import datetime, timezone

from gcpdiag.runbook import util


class TestStringConversions(unittest.TestCase):
  """Test case type converstion used for Runbook and step name converstions"""

  def test_pascal_case_to_kebab_case(self):
    self.assertEqual(util.pascal_case_to_kebab_case('PascalCase'),
                     'pascal-case')
    #should be able to handle camelcase too
    self.assertEqual(util.pascal_case_to_kebab_case('camelCase'), 'camel-case')
    self.assertEqual(util.pascal_case_to_kebab_case('Pascal'), 'pascal')
    self.assertNotEqual(util.pascal_case_to_kebab_case('Not Pascal'),
                        'not-pascal')

  def test_runbook_name_parser(self):
    self.assertEqual(util.runbook_name_parser('product/word'), 'product/word')
    self.assertEqual(util.runbook_name_parser('product/kebab-case'),
                     'product/kebab-case')
    self.assertEqual(util.runbook_name_parser('product/kebab_case_name'),
                     'product/kebab-case-name')
    self.assertEqual(util.runbook_name_parser('Product/PascalCase'),
                     'product/pascal-case')
    self.assertEqual(util.runbook_name_parser('Product/PascalCase'),
                     'product/pascal-case')

    self.assertEqual(util.runbook_name_parser('PascalCase'), 'pascal-case')
    self.assertEqual(util.runbook_name_parser('snake_case'), 'snake-case')
    self.assertEqual(util.runbook_name_parser('pascal-snake_case'),
                     'pascal-snake-case')
    self.assertEqual(util.runbook_name_parser('MixAnd-Match_Examplev3'),
                     'mix-and-match-examplev3')

  def test_parse_rfc3339_format(self):
    test_str = '2024-03-20T07:00:00Z'
    expected = datetime(2024, 3, 20, 7, 0, tzinfo=timezone.utc)
    result = util.parse_time_input(test_str)
    self.assertEqual(result, expected)

  def test_parse_epoch_format(self):
    test_str = '1601481600'  # Corresponds to 2020-09-30 16:00:00 UTC
    expected = datetime(2020, 9, 30, 16, 0, tzinfo=timezone.utc)
    result = util.parse_time_input(test_str)
    self.assertEqual(result, expected)

  def test_invalid_format_raises_error(self):
    test_str = 'not-a-valid-time'
    with self.assertRaises(ValueError):
      util.parse_time_input(test_str)
