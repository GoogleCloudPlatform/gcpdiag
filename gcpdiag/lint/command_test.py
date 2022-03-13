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

from gcpdiag import lint
from gcpdiag.lint import command


class Test:
  """Unit tests for command."""

  # pylint: disable=protected-access
  def test_flatten_multi_arg(self):
    assert list(command._flatten_multi_arg([])) == []
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
    assert args.auth_oauth is False
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
    modules = {r.product for r in repo.rules}
    assert 'gke' in modules
    assert 'gcb' in modules
    assert 'gaes' in modules
    assert 'gce' in modules
    assert 'iam' in modules
    assert 'apigee' in modules
    assert 'composer' in modules
    assert 'dataproc' in modules
    assert 'gcs' in modules
    assert 'gcf' in modules
