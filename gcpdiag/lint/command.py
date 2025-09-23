# Copyright 2021 Google LLC
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

# Lint as: python3
"""gcpdiag lint command."""

import argparse
import importlib
import logging
import pkgutil
import re
import sys

from google.auth import exceptions

from gcpdiag import config, hooks, lint, models, utils
from gcpdiag.lint.output import (api_output, csv_output, json_output,
                                 terminal_output)
from gcpdiag.queries import apis, crm, gce, kubectl


class ParseMappingArg(argparse.Action):
  """Takes a string argument and parse argument"""

  def __call__(self, parser, namespace, values, option_string):
    if values:
      if values[0] == '{' and values[-1] == '}':
        values = values[1:-1]
      values = re.split('[ ,]', values)
      parsed_dict = {}
      for value in values:
        if value:
          try:
            k, v = re.split('[:=]', value)
            parsed_dict[k] = v
          except ValueError:
            parser.error(
                f'argument {option_string} expected key:value, received {value}'
            )
    setattr(namespace, self.dest, parsed_dict)


def _flatten_multi_arg(arg_list):
  """Flatten a list of comma-separated values, like:
  ['a', 'b, c'] -> ['a','b','c']
  """
  for arg in arg_list:
    yield from re.split(r'\s*,\s*', arg)


def init_args_parser():
  parser = argparse.ArgumentParser(
      description='Run diagnostics in GCP projects.', prog='gcpdiag lint')

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

  parser.add_argument('--universe-domain',
                      type=str,
                      default=config.get('universe_domain'),
                      help='Domain name of APIs')

  parser.add_argument('--project',
                      metavar='P',
                      required=True,
                      help='Project ID of project to inspect')

  parser.add_argument(
      '--name',
      nargs='+',
      metavar='n',
      help='Resource Name(s) to inspect (e.g.: bastion-host,prod-*)')

  parser.add_argument(
      '--location',
      nargs='+',
      metavar='R',
      help=
      'Valid GCP region/zone to scope inspection (e.g.: us-central1-a,us-central1)'
  )

  parser.add_argument(
      '--label',
      action=ParseMappingArg,
      metavar='key:value',
      help=(
          'One or more resource labels as key-value pair(s) to scope inspection '
          '(e.g.: env:prod, type:frontend or env=prod type=frontend)'))

  parser.add_argument(
      '--billing-project',
      metavar='P',
      help='Project used for billing/quota of API calls done by gcpdiag '
      '(default is the inspected project, requires '
      '\'serviceusage.services.use\' permission)')

  parser.add_argument('--show-skipped',
                      help='Show skipped rules',
                      action='store_true',
                      default=config.get('show_skipped'))

  parser.add_argument('--hide-skipped',
                      help=argparse.SUPPRESS,
                      action='store_false',
                      dest='show_skipped')

  parser.add_argument('--hide-ok',
                      help='Hide rules with result OK',
                      action='store_true',
                      default=config.get('hide_ok'))

  parser.add_argument('--show-ok',
                      help=argparse.SUPPRESS,
                      action='store_false',
                      dest='hide_ok')

  parser.add_argument(
      '--enable-gce-serial-buffer',
      help='Fetch serial port one output directly from the Compute API. '
      'Use this flag when not exporting serial port output to cloud logging.',
      action='store_true',
      dest='enable_gce_serial_buffer')

  parser.add_argument(
      '--include',
      help=('Include rule pattern (e.g.: `gke`, `gke/*/2021*`). '
            'Multiple pattern can be specified (comma separated, '
            'or with multiple arguments)'),
      action='append')

  parser.add_argument('--exclude',
                      help=('Exclude rule pattern (e.g.: `BP`, `*/*/2022*`)'),
                      action='append')

  parser.add_argument('--include-extended',
                      help=('Include extended rules. Additional rules might '
                            'generate false positives (default: False)'),
                      default=config.get('include_extended'),
                      action='store_true')

  parser.add_argument('--experimental-enable-async-rules',
                      help='Run experimental async rules (default: False)',
                      default=config.get('experimental_enable_async_rules'),
                      action='store_true')

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
                      default=config.get('within_days'))

  parser.add_argument('--config',
                      metavar='FILE',
                      type=str,
                      help='Read configuration from FILE')

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

  parser.add_argument(
      '--output',
      metavar='FORMATTER',
      default='terminal',
      type=str,
      help=(
          'Format output as one of [terminal, json, csv] (default: terminal)'))

  parser.add_argument('--interface',
                      metavar='FORMATTER',
                      default=config.get('interface'),
                      type=str,
                      help='What interface as one of [cli, api] (default: cli)')

  parser.add_argument('--reason',
                      type=str,
                      default=config.get('reason'),
                      help='The reason for running gcpdiag')
  return parser


def _parse_rule_patterns(patterns):
  if patterns:
    rules = []
    for arg in _flatten_multi_arg(patterns):
      try:
        rules.append(lint.LintRulesPattern(arg))
      except ValueError as e:
        print(f"ERROR: can't parse rule pattern: {arg}", file=sys.stderr)
        raise e from None
    return rules
  return None


def _load_repository_rules(repo: lint.LintRuleRepository):
  """Find and load all lint rule modules dynamically"""
  for module in pkgutil.walk_packages(
      lint.__path__,  # type: ignore
      lint.__name__ + '.'):
    if module.ispkg:
      try:
        m = importlib.import_module(f'{module.name}')
        repo.load_rules(m)
      except ImportError as err:
        print(f"ERROR: can't import module: {err}", file=sys.stderr)
        continue


def _get_output_constructor(output_parameter_value, interface):
  if interface == 'api':
    return api_output.APIOutput
  elif output_parameter_value == 'json':
    return json_output.JSONOutput
  elif output_parameter_value == 'csv':
    return csv_output.CSVOutput
  else:
    return terminal_output.TerminalOutput


def _initialize_output(output_order):
  """Initialize output formatter."""
  constructor = _get_output_constructor(config.get('output'),
                                        config.get('interface'))
  kwargs = {
      'log_info_for_progress_only': config.get('verbose') == 0,
      'show_ok': not config.get('hide_ok'),
      'show_skipped': config.get('show_skipped'),
  }
  if config.get('interface') == 'cli':
    if config.get('output') == 'terminal':
      kwargs['output_order'] = output_order
  output = constructor(**kwargs)
  return output


def create_and_load_repo() -> lint.LintRuleRepository:
  """Helper function to initialize the repository and load rules."""
  include_patterns = _parse_rule_patterns(config.get('include'))
  exclude_patterns = _parse_rule_patterns(config.get('exclude'))

  repo = lint.LintRuleRepository(
      load_extended=config.get('include_extended'),
      run_async=config.get('experimental_enable_async_rules'),
      exclude=exclude_patterns,
      include=include_patterns,
  )
  _load_repository_rules(repo)
  return repo


def run_rules_for_context(context: models.Context,
                          repo: lint.LintRuleRepository):
  """Core function to execute lint rules against a context."""
  repo.run_rules(context)


def run(argv) -> int:
  """Run the overall command line gcpdiag lint command.

  Parsing the sys.argv and sys.exit on error for failed.

  Args:
    argv: Command line arguments.

  Returns:
    The exit code of the command.
  """
  del argv

  try:
    # 1. Initialize argument parser and configuration
    parser = init_args_parser()
    args = parser.parse_args()
    hooks.set_lint_args_hook(args)
    config.init(vars(args), terminal_output.is_cloud_shell())
    config.set_project_id(args.project)

    # 2. Perform CLI-specific validation checks
    try:
      crm.get_project(args.project)
      apis.verify_access(args.project)
    except (utils.GcpApiError, exceptions.GoogleAuthError) as e:
      print(f'[ERROR]:{e}. exiting program', file=sys.stderr)
      sys.exit(2)

    # 3. Create the linting context
    context = models.Context(
        project_id=args.project,
        locations=args.location,
        resources=args.name,
        labels=args.label,
    )

    # 4. Create and load the rule repository
    repo = create_and_load_repo()

    # 5. Set up logging and output for the terminal
    output_order = sorted(str(r) for r in repo.rules_to_run)
    output = _initialize_output(output_order=output_order)
    repo.result.add_result_handler(output.result_handler)
    logging_handler = output.get_logging_handler()
    logger = logging.getLogger()
    logger.handlers = []
    logger.addHandler(logging_handler)
    if config.get('verbose') >= 2:
      logger.setLevel(logging.DEBUG)
    else:
      logger.setLevel(logging.INFO)
    if config.get('verbose') == 0:
      gac_http_logger = logging.getLogger('apiclient.http')
      gac_http_logger.setLevel(logging.ERROR)

    if config.get('auth_oauth'):
      logger.error(
          'The oauth authentication has been deprecated and does not work'
          ' anymore. Consider using other authentication methods.')
      raise ValueError('oauth authentication is no longer supported')

    # 6. Display CLI Banner
    output.display_banner()
    output.display_header(context)

    # Warn user to fallback on serial logs buffer if project isn't storing in
    # cloud logging
    if (not gce.is_project_serial_port_logging_enabled(context.project_id) and
        not config.get('enable_gce_serial_buffer')):
      # Only print the warning if GCE is enabled in the first place
      if apis.is_enabled(context.project_id, 'compute'):
        logger.warning(
            '''Serial output to cloud logging maybe disabled for certain GCE instances.
            Fallback on serial output buffers by using flag --enable-gce-serial-buffer \n'''
        )

    # 7. Run the rules
    run_rules_for_context(context, repo)

    # 8. Display CLI Footer and clean up
    output.display_footer(repo.result)
    hooks.post_lint_hook(repo.result.get_rule_statuses())
    kubectl.clean_up()

    # 9. Exit with the correct status code
    sys.exit(2 if repo.result.any_failed else 0)

  except (utils.GcpApiError, exceptions.GoogleAuthError) as e:
    print(f'[ERROR]:{e}. exiting program', file=sys.stderr)
    sys.exit(2)
