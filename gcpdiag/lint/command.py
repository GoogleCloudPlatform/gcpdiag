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
from typing import Any, Dict, List, Optional

from gcpdiag import config, hooks, lint, models, utils
from gcpdiag.lint.output import csv_output, json_output, terminal_output
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


def _init_args_parser():
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


def _get_output_constructor(output_parameter_value):
  if output_parameter_value == 'json':
    return json_output.JSONOutput
  elif output_parameter_value == 'csv':
    return csv_output.CSVOutput
  else:
    return terminal_output.TerminalOutput


def _initialize_output(output_order):
  constructor = _get_output_constructor(config.get('output'))
  kwargs = {
      'log_info_for_progress_only': (config.get('verbose') == 0),
      'show_ok': not config.get('hide_ok'),
      'show_skipped': config.get('show_skipped')
  }
  if config.get('output') == 'terminal':
    kwargs['output_order'] = output_order
  output = constructor(**kwargs)
  return output


def _parse_args_run_repo(
    argv: Optional[List[str]] = None,
    credentials: Optional[str] = None) -> lint.LintRuleRepository:
  """Parse the sys.argv command line arguments and execute the lint rules.

  Args: argv: [str]   argument list sys.argv
        credentials: str json repr of ADC credentials

  Returns: lint.LintRuleRepository with repo results
  """
  # Initialize argument parser
  parser = _init_args_parser()
  args = parser.parse_args(args=argv)

  if credentials:
    apis.set_credentials(credentials)

  # Allow to change defaults using a hook function.
  hooks.set_lint_args_hook(args)
  # Initialize configuration
  config.init(vars(args), terminal_output.is_cloud_shell())
  try:
    # Users to use either project Number or project id
    # fetch project details
    project = crm.get_project(args.project)
  except utils.GcpApiError as e:
    # fail hard as the user typically doesn't have permission
    # to retrieve details of the project under inspection.
    print('[ERROR]:exiting program...', file=sys.stderr)
    raise ValueError('error getting project details') from e
  else:
    # set the project id in config and context as
    # remaining code will mainly use project ID
    config.set_project_id(project.id)
    # Initialize Context.
    context = models.Context(project_id=project.id,
                             locations=args.location,
                             resources=args.name,
                             labels=args.label)

  # Rules name patterns that shall be included or excluded
  include_patterns = _parse_rule_patterns(config.get('include'))
  exclude_patterns = _parse_rule_patterns(config.get('exclude'))

  # Initialize Repository, and Tests.
  repo = lint.LintRuleRepository(
      load_extended=config.get('include_extended'),
      run_async=config.get('experimental_enable_async_rules'),
      exclude=exclude_patterns,
      include=include_patterns)
  _load_repository_rules(repo)

  # ^^^ If you add rules directory, update also
  # pyinstaller/hook-gcpdiag.lint.py and bin/precommit-required-files

  # Initialize proper output formatter
  output_order = sorted(str(r) for r in repo.rules_to_run)
  output = _initialize_output(output_order=output_order)
  repo.result.add_result_handler(output.result_handler)

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

  # Deprecation warning
  if config.get('auth_oauth'):
    logger.error(
        'The oauth authentication has been deprecated and does not work'
        ' anymore. Consider using other authentication methods.')
    raise ValueError('oauth authentication is no longer supported')

  # Start the reporting
  output.display_banner()
  output.display_header(context)

  # Verify that we have access and that the CRM API is enabled
  apis.verify_access(context.project_id)

  # Warn end user to fallback on serial logs buffer if project isn't storing in
  # cloud logging
  if not gce.is_project_serial_port_logging_enabled(context.project_id) and \
    not config.get('enable_gce_serial_buffer'):
    # Only print the warning if GCE is enabled in the first place
    if apis.is_enabled(context.project_id, 'compute'):
      logger.warning(
          '''Serial output to cloud logging maybe disabled for certain GCE instances.
          Fallback on serial output buffers by using flag --enable-gce-serial-buffer \n'''
      )

  # Run the tests.
  repo.run_rules(context)
  output.display_footer(repo.result)
  hooks.post_lint_hook(repo.result.get_rule_statuses())
  if credentials:
    apis.set_credentials(None)
  # Clean up the kubeconfig file generated for gcpdiag
  kubectl.clean_up()

  return repo


def run(argv) -> int:
  """Run the overall command line gcpdiag lint command.
  Parsing the sys.argv and sys.exit on error for failed."""
  del argv

  try:
    repo = _parse_args_run_repo()
  except ValueError as e:
    print(e, file=sys.stderr)
    sys.exit(1)
  sys.exit(2 if repo.result.any_failed else 0)


def run_and_get_results(argv: List[str],
                        credentials: str = None) -> Dict[str, Any]:
  """Run gcpdiag lint as the command line and return a dict with API results.

  Args:
    argv: [str]  list of arguments like sys.argv,
    credentials: str, default credentials in json

  Returns: dict
    {'version': str, 'summary': {'ok': int, 'skipped': int, 'failed': int'},
     'result': [{'rule': str, 'resource': str, 'status': str, 'reason': str,
                 'short_info': str, 'doc_url': str}, ...]
     }
  """

  repo = _parse_args_run_repo(argv, credentials=credentials)
  results = []
  for r in repo.result.get_rule_reports():
    rule = r.rule
    rule_id = f'{rule.product}/{rule.rule_class}/{rule.rule_id}'
    for res in r.results:
      results.append({
          'rule': rule_id,
          'resource': str(res.resource or '-'),
          'status': res.status,
          'reason': res.reason,
          'short_info': res.short_info,
          'doc_url': rule.doc_url
      })
  return {
      'version': config.VERSION,
      'summary': repo.result.get_totals_by_status(),
      'result': results
  }
