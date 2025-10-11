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
"""Search command to look up gcpdiag rules"""
import argparse
import heapq
import json
import logging
from typing import Any, Dict, Iterable, List, Tuple

from blessings import Terminal

from gcpdiag import config, lint, runbook
from gcpdiag.lint import LintRule
from gcpdiag.lint import command as lint_command
from gcpdiag.runbook import DiagnosticTree
from gcpdiag.runbook import command as runbook_command
from gcpdiag.runbook.output import terminal_output


def _init_search_args_parser() -> argparse.ArgumentParser:
  """Initialize and return the argument parser for the search command."""
  parser = argparse.ArgumentParser(
      description=
      'Find gcpdiag rules like runbook and lint rules related to search terms',
      prog='gcpdiag search')

  parser.add_argument(
      'search',
      metavar='SEARCH_TERMS',
      type=str,
      nargs='*',
      help='Search terms to discover gcpdiag rules related to them')

  parser.add_argument('-q',
      '--search',
      metavar='SEARCH_TERMS',
      type=str,
      help='Search terms to discover gcpdiag rules related to them')

  parser.add_argument('-l',
                      '--limit-per-type',
                      metavar='L',
                      type=int,
                      default=10,
                      help='Limit output rules for each rule type')

  parser.add_argument('-t',
                      '--rule-type',
                      choices=['lint', 'runbook'],
                      default=['lint', 'runbook'],
                      help='Specify the type of rules to search and display')

  parser.add_argument('-p',
                      '--product',
                      metavar='PRODUCT',
                      type=str,
                      default=[],
                      action='append',
                      help='Search only rules in these products')

  parser.add_argument('-f',
                      '--format',
                      choices=['table', 'json'],
                      default='table',
                      help='Output format')

  return parser


def _load_lint_rules(args) -> Iterable[LintRule]:
  """Load and return all lint rules from the repository."""
  #pylint:disable=protected-access
  product_patterns = lint_command._parse_rule_patterns(args.product)
  repo = lint.LintRuleRepository(load_extended=True, include=product_patterns)
  #pylint:disable=protected-access
  lint_command._load_repository_rules(repo)
  return repo.rules_to_run


def _load_runbook_rules() -> Dict[str, DiagnosticTree]:
  """Load and return all runbook rules. """
  #pylint:disable=protected-access
  runbook_command._load_runbook_rules(runbook.__name__)
  return runbook.RunbookRegistry


def run(argv=None):
  """Run the search command and return the report."""
  # Initialize argument parser
  parser = _init_search_args_parser()
  args = parser.parse_args(argv)
  # Initialize configuration
  config.init(vars(args), terminal_output.is_cloud_shell())

  # Setup logging
  logger = logging.getLogger()
  logger.handlers = []
  if config.get('verbose') >= 2:
    logger.setLevel(logging.DEBUG)
  else:
    logger.setLevel(logging.INFO)
  terminal = terminal_output.TerminalOutput()
  terminal.display_banner()
  _search_rules(args)


def _rank_runbook_rules(rules: Dict,
                        args) -> List[Tuple[int, str, DiagnosticTree]]:
  """Rank runbook rules based on the keywords and return a sorted list."""
  ranked_rules: List[Tuple[int, str, DiagnosticTree]] = []
  keywords = args.search
  keywords = [kw.lower() for kw in keywords]

  for name, obj in rules.items():
    rule = obj(None)
    if args.product and rule.product not in args.product:
      continue
    rule_name = rule.id.lower()
    description = rule.__doc__.lower()
    kw_count = sum(rule.keywords.count(kw) for kw in keywords) if hasattr(
        rule, 'keywords') else 0
    name_count = sum(rule_name.count(keyword) for keyword in keywords)
    description_count = sum(description.count(keyword) for keyword in keywords)
    score = (kw_count * 3) + (name_count * 2) + description_count

    if score > 0 or args.limit_per_type == 0:
      # Use negative score to achieve a max-heap
      heapq.heappush(ranked_rules, (-score, name, rule))

  if args.limit_per_type == 0:
      return [
          heapq.heappop(ranked_rules)
          for _ in range(len(ranked_rules))
      ]
  return [
      heapq.heappop(ranked_rules)
      for _ in range(min(len(ranked_rules), args.limit_per_type))
  ]


def _rank_lint_rules(rules: Iterable[LintRule],
                     args) -> List[Tuple[int, str, LintRule]]:
  """Rank lint rules based on the keywords and return a sorted list

  """
  ranked_rules: List[Tuple[int, str, LintRule]] = []
  keywords = args.search
  print("Searching for ", keywords)
  keywords = [kw.lower() for kw in keywords]

  for rule in rules:
    name = f'{rule.product}/{rule.rule_class}/{rule.rule_id}'.lower()
    short_desc = rule.short_desc.lower()
    long_desc = rule.long_desc.lower()
    kw_count = sum(rule.keywords.count(keyword)
                   for keyword in keywords) if rule.keywords else 0
    short_desc_count = sum(short_desc.count(keyword) for keyword in keywords)
    long_desc_count = sum(long_desc.count(keyword) for keyword in keywords)
    score = (kw_count * 3) + (short_desc_count + long_desc_count) * 2

    if score > 0 or args.limit_per_type == 0:
        # Use negative score to achieve a max-heap
        heapq.heappush(ranked_rules, (-score, name, rule))

  if args.limit_per_type == 0:
      return [
          heapq.heappop(ranked_rules)
          for _ in range(len(ranked_rules))
      ]
  return [
      heapq.heappop(ranked_rules)
      for _ in range(min(len(ranked_rules), args.limit_per_type))

  ]


def _search_rules(args) -> None:
  """Search and display rules based on the search arguments."""
  matched_lint_rules = []
  matched_runbook_rules = []

  # Load the gcpdiag rules
  lint_rules = _load_lint_rules(args) if 'lint' in args.rule_type else []
  runbook_rules = _load_runbook_rules() if 'runbook' in args.rule_type else {}

  if 'lint' in args.rule_type:
    matched_lint_rules = _rank_lint_rules(lint_rules, args)
  if 'runbook' in args.rule_type:
    matched_runbook_rules = _rank_runbook_rules(runbook_rules, args)

  all_rules: Dict[str, Any] = {}
  if matched_lint_rules:
    all_rules['lint'] = [{
        'id': r[1],
        'type': 'lint',
        'description': r[2].short_desc,
        'full_description': r[2].__doc__,
        'doc_url': r[2].doc_url
    } for r in matched_lint_rules]
  if matched_runbook_rules:
    all_rules['runbook'] = []
    for r in matched_runbook_rules:
      # Make the type serializable
      for value in r[2].parameters.values():
        value['type'] = value['type'].__name__

      all_rules['runbook'].append({
          'id': r[1],
          'type': 'runbook',
          'description': r[2].short_desc,
          'full_description': r[2].__doc__,
          'doc_url': r[2].doc_url,
          'parameters': r[2].parameters
      })

  if args.format == 'json':
    print(json.dumps(all_rules, indent=2))
  else:
    _print(all_rules)


def _print(all_rules: dict) -> None:
  """Print the rules in a formatted table using native Python API and blessings for styling."""
  term = Terminal()
  # Print headings
  print(term.bold + 'Filtered Rules' + term.normal)
  print('=' * 14)

  # Print rules
  for rule_type in all_rules.values():
    for rule in rule_type:
      id_ = rule['id']
      type_ = rule['type']
      desc = rule['description']
      doc_url = rule['doc_url']
      params = ''

      print(
          f'Execution ID: {id_}\nRule Type: {type_}\nShort Description: {desc}\nDoc URL: {doc_url}'
      )
      if rule['type'] == 'runbook':
        params = ', '.join(k for k, v in rule['parameters'].items()
                           if v.get('required', False))
        print(f'Required Parameters: {params}')
        params = ', '.join(k for k, v in rule['parameters'].items()
                           if not v.get('required', False))
        print(f'Optional Parameters: {params}')
      print('')
