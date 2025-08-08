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
import sys
import unittest
from unittest import mock

from gcpdiag import config, runbook
from gcpdiag.runbook import command
from gcpdiag.runbook.exceptions import DiagnosticTreeNotFound

MUST_HAVE_MODULES = {'gce'}

sample_bundle = """
- bundle:
  parameter:
    project_id: "test-project"
    zone: "us-central1-a"
    name: "test-vm"
  steps:
    - gcpdiag.runbook.gce.generalized_steps.VmLifecycleState
    - gcpdiag.runbook.gce.ssh.PosixUserHasValidSshKeyCheck
- bundle:
  parameter:
    project_id: "test-project"
    zone: "us-central1-a"
    name: "test-vm"
  steps:
    - gcpdiag.runbook.gce.ops_agent.VmHasAServiceAccount
"""


class Test(unittest.TestCase):
  """Unit tests for command."""

  # pylint: disable=protected-access
  def test_init_args_parser(self):
    with mock.patch('os.path.exists', return_value=True):
      parser = command._init_runbook_args_parser()
      args = parser.parse_args(['product/runbook'])
      assert args.runbook == 'product/runbook'
      assert args.billing_project is None
      assert args.auth_adc is False
      assert args.auth_key is None
      assert args.verbose == 0
      assert args.logging_ratelimit_requests is None
      assert args.logging_ratelimit_period_seconds is None
      assert args.logging_page_size is None
      assert args.logging_fetch_max_entries is None
      assert args.logging_fetch_max_time_seconds is None
      assert args.auto is False
      assert args.report_dir == '/tmp'
      assert args.interface == runbook.constants.CLI

  # pylint: disable=protected-access
  def test_provided_init_args_parser(self):
    with mock.patch('os.path.exists', return_value=True):
      parser = command._init_runbook_args_parser()
      args = parser.parse_args(['product/runbook', '--auto'])
      assert args.auto is True
      args = parser.parse_args(['product/runbook', '--parameter', 'test=test'])
      assert args.parameter == {'test': 'test'}

      args = parser.parse_args(['product/runbook', '--report-dir', '~'])
      assert args.report_dir == os.path.expanduser('~')

    # Test user provided path in cloud shell in present in home.
    with mock.patch('os.getenv', return_value='true'):
      args = parser.parse_args(['product/runbook', '--report-dir', '/tmp'])
      assert args.report_dir == os.path.join(os.path.expanduser('~'),
                                             config.get('report_dir'))

    with mock.patch('os.getenv', return_value='false'):
      args = parser.parse_args(['product/runbook'])
      assert args.report_dir == os.path.join(os.path.expanduser('~'),
                                             config.get('report_dir'))

    args = parser.parse_args(['product/runbook', '--report-dir', '/tmp'])
    assert args.report_dir == '/tmp'

    args = parser.parse_args(['product/runbook', '--report-dir', '~'])
    assert args.report_dir == os.path.expanduser('~')

    args = parser.parse_args(['product/runbook', '--report-dir', '/tmp'])
    assert args.report_dir == '/tmp'

    args = parser.parse_args(['product/runbook', '--report-dir', '.'])
    assert args.report_dir == os.getcwd()

  # pylint: disable=protected-access
  def test_load_repository_rules(self):
    repo = runbook.DiagnosticEngine()
    command._load_runbook_rules(repo.__module__)
    assert len(runbook.RunbookRegistry) > 0
    modules = {r(None).product for r in runbook.RunbookRegistry.values()}
    assert MUST_HAVE_MODULES.issubset(modules)

  @mock.patch('builtins.print')
  def test_no_file_path_provided(self, mock_print):
    with self.assertRaises(SystemExit) as e:
      command._load_bundles_spec('')

    self.assertEqual(1, e.exception.code)  # sys.exit(1)
    mock_print.assert_called_once_with(
        'ERROR: no bundle spec file path provided', file=sys.stderr)

  @mock.patch('os.path.exists', return_value=False)
  @mock.patch('builtins.print')
  def test_file_does_not_exist(self, mock_print, mock_exists):
    with self.assertRaises(SystemExit):
      command._load_bundles_spec('non_existent_file.yaml')

    mock_print.assert_called_once_with(
        'ERROR: Bundle Specification file: non_existent_file.yaml does not exist!',
        file=sys.stderr)
    assert mock_exists.called

  @mock.patch('os.path.exists', return_value=True)
  @mock.patch('builtins.open',
              new_callable=mock.mock_open,
              read_data=sample_bundle)
  def test_valid_yaml_parsing(self, mock_file, mock_exists):
    result = command._load_bundles_spec('valid_file.yaml')
    self.assertIsNotNone(result)
    self.assertEqual(result[0]['parameter']['project_id'], 'test-project')
    mock_exists.assert_called_with('valid_file.yaml')
    assert mock_file.called

  def test_run_and_get_report(self):
    argv = [
        'gcpdiag runbook', 'gce/ssh', '-p', 'project_id=gcpdiag-gce1-aaaa',
        '-p', 'zone=us-central1-a', '-p', 'name=test', '--interface', 'api'
    ]
    with mock.patch('gcpdiag.runbook.DiagnosticEngine.run', side_effect=None):
      command.run_and_get_report(argv)

  def test_run_and_get_report_invalid_runbook(self):
    argv = [
        'gcpdiag runbook',
        'gce/unheaklhy',
        '-p',
        'project_id=gcpdiag-gce1-aaaa',
    ]
    with self.assertRaises(DiagnosticTreeNotFound):
      command.run_and_get_report(argv)
