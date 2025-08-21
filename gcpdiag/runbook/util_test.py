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
  """Test case type conversion used for Runbook and step name conversions."""

  def test_pascal_case_to_kebab_case(self):
    self.assertEqual(util.pascal_case_to_kebab_case('PascalCase'),
                     'pascal-case')
    # should be able to handle camelcase too
    self.assertEqual(util.pascal_case_to_kebab_case('camelCase'), 'camel-case')
    self.assertEqual(util.pascal_case_to_kebab_case('Pascal'), 'pascal')
    self.assertNotEqual(util.pascal_case_to_kebab_case('Not Pascal'),
                        'not-pascal')

  def test_pascal_case_to_title(self):
    self.assertEqual(util.pascal_case_to_title('PascalCase'), 'Pascal Case')
    self.assertEqual(util.pascal_case_to_title('Errors5xx'), 'Errors 5xx')
    self.assertEqual(util.pascal_case_to_title('Errors5xxStart'),
                     'Errors 5xx Start')
    self.assertEqual(util.pascal_case_to_title('Errors503'), 'Errors 503')

  def test_runbook_name_parser(self):
    self.assertEqual(util.runbook_name_parser('product/word'), 'product/word')
    self.assertEqual(util.runbook_name_parser('product/kebab-case'),
                     'product/kebab-case')
    self.assertEqual(
        util.runbook_name_parser('product/kebab_case_name'),
        'product/kebab-case-name',
    )
    self.assertEqual(util.runbook_name_parser('Product/PascalCase'),
                     'product/pascal-case')
    self.assertEqual(util.runbook_name_parser('Product/PascalCase'),
                     'product/pascal-case')
    self.assertEqual(
        util.runbook_name_parser('Product/PascalCase5xx'),
        'product/pascal-case-5xx',
    )
    self.assertEqual(
        util.runbook_name_parser('Product/PascalCase5Test'),
        'product/pascal-case-5-test',
    )

    self.assertEqual(util.runbook_name_parser('PascalCase'), 'pascal-case')
    self.assertEqual(util.runbook_name_parser('snake_case'), 'snake-case')
    self.assertEqual(util.runbook_name_parser('pascal-snake_case'),
                     'pascal-snake-case')
    self.assertEqual(
        util.runbook_name_parser('MixAnd-Match_Examplev3'),
        'mix-and-match-examplev-3',
    )

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


class TestGenerateUUID(unittest.TestCase):
  """Test UUID genertor for Runbook executions"""

  def test_uniqueness(self):
    """Test that generated UUIDs are unique."""
    uuids = set()
    for _ in range(10000):  # Generate a reasonable number of UUIDs
      uuids.add(util.generate_uuid())
    self.assertEqual(len(uuids), 10000)  # All should be unique

  def test_default_parameters(self):
    """Test with default length and separator."""
    result = util.generate_uuid()

    self.assertEqual(len(result), 10 + result.count('.'))  # Check length
    self.assertTrue('.' in result)  # Check for separator

  def test_custom_length(self):
    """Test with a custom length."""
    result = util.generate_uuid(length=12)
    self.assertEqual(len(result), 12 + result.count('.'))

  def test_custom_separator(self):
    """Test with a custom separator."""
    result = util.generate_uuid(separator='-')
    self.assertTrue('-' in result)

  def test_custom_interval(self):
    """Test with a custom separator interval."""
    result = util.generate_uuid(separator_interval=3)
    separator_count = result.count('.')
    self.assertEqual(separator_count, 3)

  def test_truncate(self):
    """Test truncation when length is shorter than UUID."""
    result = util.generate_uuid(length=4)
    self.assertEqual(len(result), 4 + result.count('.'))

  def test_pad(self):
    """Test padding when length is longer than UUID."""
    result = util.generate_uuid(length=40)
    self.assertEqual(len(result), 40 + result.count('.'))
    self.assertTrue(result.endswith('0'))
