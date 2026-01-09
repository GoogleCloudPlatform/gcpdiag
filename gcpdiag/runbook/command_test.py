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
import argparse
import os
import sys
import unittest
from unittest import mock

from gcpdiag import config, models, runbook
from gcpdiag.queries import apis_stub
from gcpdiag.runbook import command
from gcpdiag.runbook.exceptions import DiagnosticTreeNotFound
from gcpdiag.runbook.output import api_output, base_output

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
        'ERROR: Bundle Specification file: non_existent_file.yaml does not'
        ' exist!',
        file=sys.stderr,
    )
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

  @mock.patch('gcpdiag.queries.apis.get_api', new=apis_stub.get_api_stub)
  @mock.patch('gcpdiag.queries.apis.get_user_email',
              return_value='test@example.com')
  def test_run_and_get_report(self, mock_get_user_email):
    del mock_get_user_email
    argv = [
        'gcpdiag runbook', 'gce/ssh', '-p',
        'project_id=gcpdiag-gce-faultyssh-runbook', '-p', 'zone=europe-west2-a',
        '-p', 'name=faulty-linux-ssh', '--interface', 'api', '--auto'
    ]
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

  def test_parse_mapping_arg_with_braces(self):
    parser = mock.Mock()
    namespace = argparse.Namespace()
    namespace.parameter = models.Parameter()
    action = command.ParseMappingArg(option_strings=['-p'], dest='parameter')
    values = '{key=value,key2=value2}'
    action(parser, namespace, values, '-p')
    self.assertEqual(namespace.parameter['key'], 'value')
    self.assertEqual(namespace.parameter['key2'], 'value2')

  def test_parse_mapping_arg_value_error(self):
    """Ensures ParseMappingArg calls parser.error on invalid key=value format."""
    parser = mock.Mock()
    namespace = mock.Mock()
    action = command.ParseMappingArg(option_strings=['-p'], dest='parameter')
    invalid_value = ['invalid_format']  # Missing '='
    action(parser, namespace, invalid_value, '-p')
    parser.error.assert_called_once()
    self.assertIn('expected key:value', parser.error.call_args[0][0])

  @mock.patch('os.path.exists', return_value=True)
  @mock.patch('os.path.abspath', side_effect=lambda x: x)
  @mock.patch('os.getenv')
  def test_expand_path_cloud_shell_outside_home(self, mock_getenv,
                                                unused_mock_abspath,
                                                unused_mock_exists):
    """Ensures an error is raised in Cloud Shell if the path is not in HOME."""
    mock_getenv.side_effect = lambda k: 'true' if k == 'CLOUD_SHELL' else None
    user_supplied_path = '/etc/invalid'
    with self.assertRaises(argparse.ArgumentTypeError) as cm:
      command.expand_and_validate_path(user_supplied_path)
    self.assertIn('must be located in your home directory', str(cm.exception))

  @mock.patch('builtins.print')
  def test_validate_args_missing_inputs(self, mock_print):
    """Ensures validate_args prints an error when no runbook or bundle is provided."""
    args = mock.Mock()
    args.runbook = None
    args.bundle_spec = []
    command.validate_args(args)
    mock_print.assert_called_once_with(
        'Error: Provide a runbook id  or "--bundle-spec=YAML_FILE_PATH" must be'
        ' provided.')

  @mock.patch('importlib.import_module')
  @mock.patch('pkgutil.walk_packages')
  def test_load_runbook_rules_import_error(self, mock_walk, mock_import):
    """Ensures _load_runbook_rules continues execution on ImportError."""
    mock_pkg = mock.Mock()
    mock_pkg.__path__ = ['/path']
    mock_pkg.__name__ = 'pkg'
    mock_import.side_effect = [mock_pkg, ImportError('Mock error')]
    mock_walk.return_value = [(None, 'pkg.bad_module', False)]
    command._load_runbook_rules('pkg')
    self.assertTrue(mock_import.called)

  @mock.patch('os.path.exists', return_value=True)
  @mock.patch('builtins.open',
              new_callable=mock.mock_open,
              read_data='!!invalid_yaml')
  def test_load_bundles_spec_yaml_error(self, unused_mock_file,
                                        unused_mock_exists):
    """Ensures _load_bundles_spec exits on invalid YAML content."""
    with self.assertRaises(SystemExit):
      command._load_bundles_spec('invalid.yaml')

  @mock.patch('os.path.exists', return_value=True)
  @mock.patch('os.path.abspath', side_effect=lambda x: x)
  @mock.patch('os.getenv', return_value='true')  # Simulates CLOUD_SHELL=true
  def test_expand_path_cloud_shell_valid(self, unused_mock_getenv,
                                         unused_mock_abspath,
                                         unused_mock_exists):
    """Ensures paths are correctly joined with HOME in Cloud Shell."""
    home = os.path.expanduser('~')
    report_dir = config.get('report_dir')
    result = command.expand_and_validate_path(report_dir)
    self.assertEqual(result, os.path.join(home, report_dir))

  def test_initialize_output_api(self):
    """Ensures ApiOutput is initialized when interface is 'api'."""
    output = command._initialize_output(runbook.constants.API)
    self.assertIsInstance(output, api_output.ApiOutput)

  def test_initialize_output_base(self):
    """Ensures BaseOutput is used for unknown interfaces."""
    output = command._initialize_output('unknown')
    self.assertIsInstance(output, base_output.BaseOutput)

  @mock.patch('gcpdiag.runbook.DiagnosticEngine')
  @mock.patch('gcpdiag.runbook.command._initialize_output')
  def test_run_and_get_report_bundle_spec(self, mock_init_output,
                                          mock_engine_cls):
    """Exercises the bundle_spec logic path in run_and_get_report."""
    mock_init_output.return_value = mock.Mock()
    mock_engine = mock_engine_cls.return_value
    mock_engine.interface.rm.generate_reports.return_value = {}
    mock_run = mock_engine.run
    mock_load_steps = mock_engine.load_steps
    mock_bundle = mock.Mock()
    mock_bundle.parameter = {'p': 'v'}
    mock_load_steps.return_value = mock_bundle
    with mock.patch('builtins.open', mock.mock_open(read_data='')):
      with mock.patch('gcpdiag.runbook.command._load_bundles_spec',
                      return_value=[{
                          'parameter': {
                              'p': 'v'
                          },
                          'steps': ['s']
                      }]):
        argv = ['gcpdiag runbook', '--bundle-spec', 'test.yaml']
        command.run_and_get_report(argv)
        self.assertTrue(mock_run.called)
        self.assertTrue(mock_load_steps.called)

  @mock.patch('gcpdiag.runbook.command.run_and_get_report')
  @mock.patch('logging.error')
  def test_run_logs_exceptions(self, mock_log, mock_run_report):
    """Ensures exceptions in run_and_get_report are logged."""
    mock_run_report.side_effect = DiagnosticTreeNotFound('Test Error')
    command.run(['gcpdiag runbook'])
    mock_log.assert_called_once()

  @mock.patch('gcpdiag.queries.apis.get_api', new=apis_stub.get_api_stub)
  @mock.patch('gcpdiag.queries.apis.get_user_email',
              return_value='test@example.com')
  @mock.patch('gcpdiag.runbook.command._initialize_output')
  @mock.patch('gcpdiag.queries.apis.set_credentials')
  @mock.patch('gcpdiag.hooks.post_runbook_hook')
  @mock.patch('gcpdiag.queries.kubectl.clean_up')
  def test_run_and_get_report_full_flow(self, mock_kube, mock_hook, mock_creds,
                                        mock_out, mock_get_user_email):
    """
    Tests the full flow of run_and_get_report with API stubs.

    Args:
      mock_kube: Mock of gcpdiag.queries.kubectl.clean_up.
      mock_hook: Mock of gcpdiag.hooks.post_runbook_hook.
      mock_creds: Mock of gcpdiag.queries.apis.set_credentials.
      mock_out: Mock of gcpdiag.runbook.command._initialize_output.
      mock_get_user_email: Mock of gcpdiag.queries.apis.get_user_email.
    """
    del mock_get_user_email
    mock_output_obj = mock.Mock()
    mock_out.return_value = mock_output_obj
    mock_handler = mock.Mock()
    mock_handler.level = 0
    mock_output_obj.get_logging_handler.return_value = mock_handler
    argv = [
        'gcpdiag runbook', 'gce/ssh', '-p',
        'project_id=gcpdiag-gce-faultyssh-runbook', '-p', 'zone=europe-west2-a',
        '-p', 'name=faulty-linux-ssh', '--interface', 'cli', '--auto'
    ]
    report = command.run_and_get_report(argv, credentials='creds')
    mock_creds.assert_called_once_with('creds')
    mock_output_obj.display_header.assert_called_once()
    self.assertIn('version', report)
    self.assertTrue(mock_hook.called)
    mock_output_obj.display_footer.assert_called_once()
    mock_kube.assert_called_once()
