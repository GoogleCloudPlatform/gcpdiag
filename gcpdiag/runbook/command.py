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
"""gcpdiag runbook command."""

import argparse
import importlib
import logging
import pkgutil
import re
import sys

from gcpdiag import config, hooks, models, runbook
from gcpdiag.queries import apis, crm, kubectl
from gcpdiag.runbook.output import terminal_output


class ParseMappingArg(argparse.Action):
  """Takes a string argument and parse argument"""

  def __call__(self, parser, namespace, values, option_string):
    if values:
      if values[0] == '{' and values[-1] == '}':
        values = values[1:-1]
      if not isinstance(values, list):
        values = re.split('[ ,]', values)
      parsed_dict = getattr(namespace, self.dest, {})
      for value in values:
        if value:
          try:
            k, v = re.split('[=]', value)
            parsed_dict[k] = v
          except ValueError:
            parser.error(
                f'argument {option_string} expected key:value, received {value}'
            )
    setattr(namespace, self.dest, parsed_dict)


def _init_runbook_args_parser():
  parser = argparse.ArgumentParser(
      description='Run diagnostics in GCP projects.', prog='gcpdiag runbook')

  parser.add_argument(
      '--auth-adc',
      help='Authenticate using Application Default Credentials (default)',
      action='store_true')

  parser.add_argument(
      '--auth-key',
      help='Authenticate using a service account private key file',
      metavar='FILE')

  parser.add_argument('--auth-oauth',
                      help=argparse.SUPPRESS,
                      action='store_true')

  parser.add_argument('--project',
                      metavar='P',
                      required=True,
                      help='Project ID of project to inspect')

  parser.add_argument(
      '--billing-project',
      metavar='P',
      help='Project used for billing/quota of API calls done by gcpdiag '
      '(default is the inspected project, requires '
      '\'serviceusage.services.use\' permission)')

  parser.add_argument('-v',
                      '--verbose',
                      action='count',
                      default=config.get('verbose'),
                      help='Increase log verbosity')

  parser.add_argument('--within-days',
                      metavar='D',
                      type=int,
                      help=(f'How far back to search logs and metrics (default:'
                            f" {config.get('within_days')} days)"),
                      default=1)

  parser.add_argument('--config',
                      metavar='FILE',
                      type=str,
                      help=('Read configuration from FILE'))

  parser.add_argument('--logging-ratelimit-requests',
                      metavar='R',
                      type=int,
                      help=('Configure rate limit for logging queries (default:'
                            f" {config.get('logging_ratelimit_requests')})"))

  parser.add_argument(
      '--logging-ratelimit-period-seconds',
      metavar='S',
      type=int,
      help=('Configure rate limit period for logging queries (default:'
            f" {config.get('logging_ratelimit_period_seconds')} seconds)"))

  parser.add_argument('--logging-page-size',
                      metavar='P',
                      type=int,
                      help=('Configure page size for logging queries (default:'
                            f" {config.get('logging_page_size')})"))

  parser.add_argument(
      '--logging-fetch-max-entries',
      metavar='E',
      type=int,
      help=('Configure max entries to fetch by logging queries (default:'
            f" {config.get('logging_fetch_max_entries')})"))

  parser.add_argument(
      '--logging-fetch-max-time-seconds',
      metavar='S',
      type=int,
      help=('Configure timeout for logging queries (default:'
            f" {config.get('logging_fetch_max_time_seconds')} seconds)"))

  parser.add_argument('runbook',
                      nargs='+',
                      help=('Runbook to execute in the format product/name'))
  parser.add_argument(
      '-p',
      '--parameter',
      action=ParseMappingArg,
      nargs=1,
      default={},
      dest='parameter',
      metavar='key:value',
      help=
      ('One or more resource parameters as key-value pair(s) to scope inspection '
       '(e.g.: -p source_ip=xx:xx:xx:xx -p user:user@company.com)'))

  parser.add_argument(
      '-a',
      '--auto',
      help=('Execute runbook autonomously. Use this to skip human tasks. '
            'Incomplete tasks are added to the report.'),
      action='store_true')

  parser.add_argument(
      '--label',
      action=ParseMappingArg,
      metavar='key:value',
      help=(
          'One or more resource labels as key-value pair(s) to scope inspection '
          '(e.g.: env:prod, type:frontend or env=prod type=frontend)'))

  return parser


def _flatten_multi_arg(arg_list):
  """Flatten a list of comma-separated values, like:
  ['a', 'b, c'] -> ['a','b','c']
  """
  for arg in arg_list:
    yield from re.split(r'\s*,\s*', arg)


def _parse_rule_patterns(patterns):
  if patterns:
    rules = []
    for arg in _flatten_multi_arg(patterns):
      try:
        rules.append(runbook.RunbookRulesPattern(arg))
      except ValueError:
        print(f"ERROR: can't parse rule pattern: {arg}", file=sys.stderr)
        sys.exit(1)
    return rules
  return None


def _load_repository_rules(repo: runbook.RunbookRuleRepository):
  """Find and load all lint rule modules dynamically"""
  for module in pkgutil.walk_packages(
      runbook.__path__,  # type: ignore
      runbook.__name__ + '.'):
    if module.ispkg:
      try:
        m = importlib.import_module(f'{module.name}')
        repo.load_rules(m)
      except ImportError as err:
        print(f"ERROR: can't import module: {err}", file=sys.stderr)
        continue


def _initialize_output(output_order):
  constructor = terminal_output.TerminalOutput
  kwargs = {
      'log_info_for_progress_only': (config.get('verbose') == 0),
  }
  if config.get('output') == 'terminal':
    kwargs['output_order'] = output_order
  output = constructor(**kwargs)
  return output


def run(argv) -> int:
  del argv

  # Initialize argument parser
  parser = _init_runbook_args_parser()
  args = parser.parse_args()

  # Allow to change defaults using a hook function.
  hooks.set_lint_args_hook(args)

  # Initialize configuration
  config.init(vars(args), terminal_output.is_cloud_shell())
  project = crm.get_project(args.project)
  config.set_project_id(project.id)

  # Initialize Context.
  context = models.Context(project_id=project.id, parameters=args.parameter)

  # Rules name patterns that shall be included or excluded
  runbook_patterns = _parse_rule_patterns(args.runbook)

  # Initialize Repository, and Tests.
  repo = runbook.RunbookRuleRepository(runbook=runbook_patterns)
  _load_repository_rules(repo)

  # ^^^ If you add rules directory, update also
  # pyinstaller/hook-gcpdiag.lint.py and bin/precommit-required-files

  # Initialize proper output formater
  output_order = sorted(str(r) for r in repo.rules_to_run)
  output = _initialize_output(output_order=output_order)
  repo.report.add_result_handler(output.result_handler)

  # Logging setup.
  logging_handler = output.get_logging_handler()
  logger = logging.getLogger()
  # Make sure we are only using our own handler
  logger.handlers = []
  logger.addHandler(logging_handler)
  if config.get('verbose') >= 2:
    logger.setLevel(logging.DEBUG)
  else:
    logger.setLevel(logging.INFO)
  # Disable logging from python-api-client, unless verbose is turned on
  if config.get('verbose') == 0:
    gac_http_logger = logging.getLogger('googleapiclient.http')
    gac_http_logger.setLevel(logging.ERROR)

  # Start the reporting
  output.display_banner()
  output.display_header(context)

  # Verify that we have access and that the CRM API is enabled
  apis.verify_access(context.project_id)

  # Run the tests.
  repo.run_rules(context)
  output.display_footer(repo.report)
  hooks.post_lint_hook(repo.report.get_rule_statuses())

  # Clean up the kubeconfig file generated for gcpdiag
  kubectl.clean_up()

  # Exit 0 if there are no failed rules.
  sys.exit(2 if repo.report.any_failed else 0)
