# Copyright 2024 Google LLC
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
""" Test gcpdiag search command"""
import unittest
from argparse import Namespace
from unittest import mock

from gcpdiag.lint import LintRule
from gcpdiag.runbook import DiagnosticTree
from gcpdiag.search import command as search_cmd


class TestGcpdiagSearchCommand(unittest.TestCase):
  """Unit tests for gcpdiag search command argument parsing and rule searching."""

  # pylint: disable=protected-access

  def setUp(self):
    self.parser = search_cmd._init_search_args_parser()

  def test_no_search_terms(self):
    """Test case when no search terms are provided."""
    with self.assertRaises(SystemExit):
      self.parser.parse_args([])

  def test_single_search_term(self):
    """Test case with a single search term."""
    args = self.parser.parse_args(['test-keyword'])
    self.assertEqual(args.search, ['test-keyword'])
    self.assertEqual(args.limit_per_type, 10)
    self.assertEqual(args.rule_type, ['lint', 'runbook'])
    self.assertEqual(args.product, [])
    self.assertEqual(args.format, 'table')

  def test_multiple_search_terms(self):
    """Test case with multiple search terms."""
    args = self.parser.parse_args(['test-keyword', 'public'])
    self.assertEqual(args.search, ['test-keyword', 'public'])

  def test_limit_argument(self):
    """Test case with the limit argument."""
    args = self.parser.parse_args(['test-keyword', '--limit-per-type', '5'])
    self.assertEqual(args.limit_per_type, 5)

  def test_rule_type_argument(self):
    """Test case with the rule-type argument."""
    args = self.parser.parse_args(['test-keyword', '--rule-type', 'lint'])
    self.assertEqual(args.rule_type, 'lint')

  def test_product_argument(self):
    """Test case with the product argument."""
    args = self.parser.parse_args(['test-keyword', '--product', 'prod'])
    self.assertEqual(args.product, ['prod'])

  def test_format_argument(self):
    """Test case with the format argument."""
    args = self.parser.parse_args(['test-keyword', '--format', 'json'])
    self.assertEqual(args.format, 'json')

  def test_all_arguments(self):
    """Test case with all arguments."""
    args = self.parser.parse_args([
        'test-keyword', 'public', '--limit-per-type', '2', '--rule-type',
        'runbook', '--product', 'prod', '--format', 'json'
    ])
    self.assertEqual(args.search, ['test-keyword', 'public'])
    self.assertEqual(args.limit_per_type, 2)
    self.assertEqual(args.rule_type, 'runbook')
    self.assertEqual(args.product, ['prod'])
    self.assertEqual(args.format, 'json')

  @mock.patch('gcpdiag.search.command._load_lint_rules')
  @mock.patch('gcpdiag.search.command._load_runbook_rules')
  def test_search_rules(self, mock_load_runbook_rules, mock_load_lint_rules):
    """Test case for search rules functionality."""
    mock_load_lint_rules.return_value = []
    mock_load_runbook_rules.return_value = {}

    args = self.parser.parse_args([
        'test-keyword', 'public', '--limit-per-type', '2', '--rule-type',
        'runbook', '--product', 'prod'
    ])

    search_cmd._search_rules(args)

    mock_load_lint_rules.assert_not_called()
    mock_load_runbook_rules.assert_called_once()

  @mock.patch('gcpdiag.search.command._print')
  @mock.patch('gcpdiag.search.command._rank_runbook_rules')
  @mock.patch('gcpdiag.search.command._rank_lint_rules')
  def test_search_rules_output(self, mock_rank_lint_rules,
                               mock_rank_runbook_rules, mock_print):
    """Test case for search rules output functionality."""
    mock_rank_lint_rules.return_value = []
    mock_rank_runbook_rules.return_value = []

    args = self.parser.parse_args([
        'test-keyword', 'public', '--limit-per-type', '2', '--rule-type',
        'runbook', '--product', 'prod'
    ])

    search_cmd._search_rules(args)

    mock_print.assert_called_once_with({})


class TestRankingFunctions(unittest.TestCase):
  """Unit tests for ranking functions in gcpdiag search command."""

  # pylint: disable=protected-access

  class TestDT1(DiagnosticTree):
    id = 'rule1'
    product = 'prod'
    __doc__ = 'This is a test rule for test-issue'
    keywords = ['issue-kw', 'public']

  class TestDT2(DiagnosticTree):
    id = 'rule2'
    product = 'prod'
    __doc__ = 'Another test rule for issue-kw2'
    keywords = ['issue-kw2', 'engine']

  class TestDT3(DiagnosticTree):
    id = 'rule3'
    product = 'another-prod'
    __doc__ = 'Another test rule for storage'
    keywords = ['storage']

  def setUp(self):
    self.runbook_rules = {
        'rule1': self.TestDT1,
        'rule2': self.TestDT2,
        'rule3': self.TestDT3
    }

    self.lint_rules = [
        LintRule(product='prod',
                 rule_class='class1',
                 rule_id='rule1',
                 short_desc='Test lint rule for SSH',
                 long_desc='Detailed desc about SSH and issue-kw2',
                 keywords=['issue-kw', 'issue-kw2', 'lint']),
        LintRule(product='prod',
                 rule_class='class2',
                 rule_id='rule2',
                 short_desc='Another lint rule for engine',
                 long_desc='Detailed desc about engine',
                 keywords=['engine']),
        LintRule(product='another-prod',
                 rule_class='class1',
                 rule_id='rule3',
                 short_desc='Rule for storage',
                 long_desc='Detailed desc about storage',
                 keywords=['storage', 'public']),
    ]

  def test_rank_runbook_rules_max_heap(self):
    """Test case for ensuring max-heap behavior in runbook rules ranking."""
    args = Namespace(search=['test'], limit_per_type=2, product=['search'])
    ranked_rules = search_cmd._rank_runbook_rules(self.runbook_rules, args)

    self.assertEqual(len(ranked_rules), 2)
    # Ensure the highest score is first
    self.assertTrue(-ranked_rules[0][0] >= -ranked_rules[1][0])

  def test_rank_runbook_rules_frequency(self):
    """Test case for ensuring correct frequency calculation in runbook rules ranking."""
    args = Namespace(search=['issue-kw', 'public'],
                     limit_per_type=2,
                     product=['search'])
    ranked_rules = search_cmd._rank_runbook_rules(self.runbook_rules, args)

    self.assertEqual(len(ranked_rules), 2)
    score, name, _ = ranked_rules[0]
    self.assertEqual(name, 'rule1')
    self.assertEqual(-score, 6)  # 3 for keyword 'issue-kw' and 3 for 'public'

  def test_rank_lint_rules_frequency(self):
    """Test case for ensuring correct frequency calculation in lint rules ranking."""
    args = Namespace(search=['issue-kw', 'issue-kw2'],
                     limit_per_type=2,
                     product=['prod'])
    ranked_rules = search_cmd._rank_lint_rules(self.lint_rules, args)

    self.assertEqual(len(ranked_rules), 1)
    score, name, _ = ranked_rules[0]
    self.assertEqual(name, 'prod/class1/rule1')
    self.assertEqual(
        -score, 10
    )  # 3 for keyword 'issue-kw', 'issue-kw2' and 2 for 'issue-kw2' in description

  def test_rank_lint_rules_max_heap(self):
    """Test case for ensuring max-heap behavior in lint rules ranking."""
    args = Namespace(search=['lint', 'rule'],
                     limit_per_type=3,
                     product=['prod', 'another-prod'])
    ranked_rules = search_cmd._rank_lint_rules(self.lint_rules, args)

    self.assertEqual(len(ranked_rules), 3)
    # Ensure the highest score is first
    self.assertTrue(-ranked_rules[0][0] >= -ranked_rules[1][0])
    self.assertTrue(-ranked_rules[1][0] >= -ranked_rules[2][0])
