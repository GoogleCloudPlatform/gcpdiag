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
"""Test code in command.py."""

import sys
from unittest import TestCase, mock

from gcpdiag import config, lint
from gcpdiag.lint import command
from gcpdiag.queries import apis, apis_stub

MUST_HAVE_MODULES = {
    'gke', 'gcb', 'gae', 'gce', 'iam', 'apigee', 'composer', 'datafusion',
    'dataproc', 'gcs', 'vpc', 'lb', 'gcf'
}


@mock.patch('sys.exit', side_effect=lambda x: None)
@mock.patch.object(apis, 'get_user_email', return_value='someone@company.com')
@mock.patch('gcpdiag.queries.apis.get_api', new=apis_stub.get_api_stub)
class TestCommand(TestCase):
  """Unit tests for overall command execution."""

  def test_run(self, mock_email, mock_api):
    # pylint: disable=W0613

    sys.argv = [
        'gcpdiag lint',
        '--project',
        '12340001',
        '--include',
        'dataproc/BP/2021_001',
    ]
    command.run([])
    assert True

  def test_run_and_get_results(self, mock_email, mock_api):
    # pylint: disable=W0613
    sys.argv = [
        'gcpdiag lint',
        '--project',
        '12340001',
        '--include',
        'dataproc/BP/2021_001',
    ]
    self.assertDictEqual(
        command.run_and_get_results(None), {
            'result': [{
                'doc_url': 'https://gcpdiag.dev/rules/dataproc/BP/2021_001',
                'long_doc': 'Enabling stackdriver logging for your Dataproc '
                            'cluster impacts the ability\n'
                            'to troubleshoot any issues that you might have.',
                'result': [{
                    'reason': 'no dataproc clusters found',
                    'resource': '-',
                    'status': 'skipped'
                }],
                'rule': 'dataproc/BP/2021_001',
                'short_doc':
                    'Check if logging is enabled : Stackdriver Logging '
                    'enabled'
            }],
            'summary': {
                'skipped': 1
            },
            'version': config.VERSION
        })


class Test:
  """Unit tests for command."""

  # pylint: disable=protected-access
  def test_flatten_multi_arg(self):
    assert not list(command._flatten_multi_arg([]))
    assert list(command._flatten_multi_arg(['*BP*'])) == ['*BP*']
    assert list(command._flatten_multi_arg(['*BP*',
                                            '*ERR*'])) == ['*BP*', '*ERR*']
    assert list(command._flatten_multi_arg(['*BP*,*ERR*'])) == ['*BP*', '*ERR*']
    assert list(command._flatten_multi_arg(['*BP*, *ERR*'
                                           ])) == ['*BP*', '*ERR*']

  # pylint: disable=protected-access
  def test_init_args_parser(self):
    parser = command._init_args_parser()
    args = parser.parse_args(['--project', 'myproject'])
    assert args.project == 'myproject'
    assert args.billing_project is None
    assert args.auth_adc is False
    assert args.auth_key is None
    assert args.verbose == 0
    assert args.within_days == 3
    assert args.include is None
    assert args.exclude is None
    assert args.include_extended is False
    assert args.config is None
    assert args.show_skipped is False
    assert args.hide_ok is False
    assert args.logging_ratelimit_requests is None
    assert args.logging_ratelimit_period_seconds is None
    assert args.logging_page_size is None
    assert args.logging_fetch_max_entries is None
    assert args.logging_fetch_max_time_seconds is None
    assert args.output == 'terminal'
    assert args.enable_gce_serial_buffer is False

  # pylint: disable=protected-access
  def test_provided_init_args_parser(self):
    parser = command._init_args_parser()
    args = parser.parse_args(['--project', 'myproject', '--include', '*ERR*'])
    assert args.include == ['*ERR*']
    args = parser.parse_args(['--project', 'myproject', '--exclude', '*BP*'])
    assert args.exclude == ['*BP*']
    args = parser.parse_args(['--project', 'myproject', '--include-extended'])
    assert args.include_extended is True
    args = parser.parse_args(
        ['--project', 'myproject', '--config', '/path/to/file'])
    assert args.config == '/path/to/file'

  # pylint: disable=protected-access
  def test_load_repository_rules(self):
    repo = lint.LintRuleRepository()
    command._load_repository_rules(repo)
    modules = {r.product for r in repo.rules_to_run}
    assert MUST_HAVE_MODULES.issubset(modules)

  def test_parse_label(self):
    parser = command._init_args_parser()
    # Test with a single value
    args = parser.parse_args(['--project', 'x', '--label', 'key=value'])
    assert args.label == {'key': 'value'}

    # Test with multiple values
    args = parser.parse_args(
        ['--project', 'x', '--label', 'key1:value1,  key2=value2'])
    assert args.label == {'key1': 'value1', 'key2': 'value2'}

    # Test with curly braces
    args = parser.parse_args(
        ['--project', 'x', '--label', '{ key1=value1, key2=value2 }'])
    assert args.label == {'key1': 'value1', 'key2': 'value2'}

    # Test with mapping separated by commas
    args = parser.parse_args(
        ['--project', 'x', '--label', 'key1=value1,key2:value2'])
    assert args.label == {'key1': 'value1', 'key2': 'value2'}

    # Test with values separated by spaces
    args = parser.parse_args(
        ['--project', 'x', '--label', '  key1=value1 key2:value2  '])
    assert args.label == {'key1': 'value1', 'key2': 'value2'}

    # exit if invalid --label value is provided.
    try:
      args = parser.parse_args(['--project', 'x', '--label', 'invalid'])
    except SystemExit as e:
      assert e.code == 2
