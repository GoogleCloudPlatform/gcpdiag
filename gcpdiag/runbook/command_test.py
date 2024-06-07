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
"""Test code in command.py."""
import os
import unittest
from unittest import mock

from gcpdiag import config, runbook
from gcpdiag.runbook import command

MUST_HAVE_MODULES = {'gce'}


class Test(unittest.TestCase):
  """Unit tests for command."""

  # pylint: disable=protected-access
  def test_init_args_parser(self):
    with mock.patch('os.path.exists', return_value=True):
      parser = command._init_runbook_args_parser()
      args = parser.parse_args(['product/runbook', '--project', 'myproject'])
      assert args.project == 'myproject'
      assert args.runbook == 'product/runbook'
      assert args.billing_project is None
      assert args.auth_adc is False
      assert args.auth_key is None
      assert args.verbose == 0
      assert args.within_days == 1
      assert args.logging_ratelimit_requests is None
      assert args.logging_ratelimit_period_seconds is None
      assert args.logging_page_size is None
      assert args.logging_fetch_max_entries is None
      assert args.logging_fetch_max_time_seconds is None
      assert args.auto is False
      assert args.report_dir == '/tmp'
      assert args.interface == 'cli'

  # pylint: disable=protected-access
  def test_provided_init_args_parser(self):
    with mock.patch('os.path.exists', return_value=True):
      parser = command._init_runbook_args_parser()
      args = parser.parse_args(
          ['product/runbook', '--project', 'myproject', '--auto'])
      assert args.auto is True
      args = parser.parse_args([
          'product/runbook', '--project', 'myproject', '--parameter',
          'test=test'
      ])
      assert args.parameter == {'test': 'test'}

      args = parser.parse_args(
          ['product/runbook', '--project', 'myproject', '--report-dir', '~'])
      assert args.report_dir == os.path.expanduser('~')

    # Test user provided path in cloud shell in present in home.
    with mock.patch('os.getenv', return_value='true'):
      args = parser.parse_args(
          ['product/runbook', '--project', 'myproject', '--report-dir', '/tmp'])
      assert args.report_dir == os.path.join(os.path.expanduser('~'),
                                             config.get('report_dir'))

    with mock.patch('os.getenv', return_value='false'):
      args = parser.parse_args(['product/runbook', '--project', 'myproject'])
      assert args.report_dir == os.path.join(os.path.expanduser('~'),
                                             config.get('report_dir'))

    args = parser.parse_args(
        ['product/runbook', '--project', 'myproject', '--report-dir', '/tmp'])
    assert args.report_dir == '/tmp'

    args = parser.parse_args(
        ['product/runbook', '--project', 'myproject', '--report-dir', '~'])
    assert args.report_dir == os.path.expanduser('~')

    args = parser.parse_args(
        ['product/runbook', '--project', 'myproject', '--report-dir', '/tmp'])
    assert args.report_dir == '/tmp'

    args = parser.parse_args(
        ['product/runbook', '--project', 'myproject', '--report-dir', '.'])
    assert args.report_dir == os.getcwd()

  # pylint: disable=protected-access
  def test_load_repository_rules(self):
    repo = runbook.DiagnosticEngine()
    command._load_runbook_rules(repo.__module__)
    assert len(runbook.DiagnosticTreeRegister) > 0
    modules = {r(None).product for r in runbook.DiagnosticTreeRegister.values()}
    assert MUST_HAVE_MODULES.issubset(modules)

  def test_validate_rule_pattern(self):
    # Valid patterns
    self.assertEqual('gcp/runbook-id',
                     command._validate_rule_pattern('gcp/runbook-id'))
    self.assertEqual('gcp/runbook-id',
                     command._validate_rule_pattern('GCP/runbook-id'))
    self.assertEqual('gcp/runbook-id-one',
                     command._validate_rule_pattern('gcp/runbook-id-one'))

    # Invalid patterns
    with self.assertRaises(SystemExit) as e:
      command._validate_rule_pattern('gcp')
    self.assertEqual(2, e.exception.code)
    with self.assertRaises(SystemExit) as e:
      command._validate_rule_pattern('runbook-id')
    self.assertEqual(2, e.exception.code)
    with self.assertRaises(SystemExit) as e:
      command._validate_rule_pattern('gcp/runbook-id/1/2/3/4')
    self.assertEqual(2, e.exception.code)
    with self.assertRaises(SystemExit) as e:
      command._validate_rule_pattern('gcp/runbook_id')
    self.assertEqual(2, e.exception.code)
    with self.assertRaises(SystemExit) as e:
      command._validate_rule_pattern(r'gcp/runbook\id')
    self.assertEqual(2, e.exception.code)
