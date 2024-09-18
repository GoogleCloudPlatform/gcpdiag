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
import os
import pkgutil
import re
import sys
import warnings
from typing import List

import yaml

from gcpdiag import config, hooks, models, runbook
from gcpdiag.queries import apis, kubectl
from gcpdiag.runbook.output import terminal_output


class ParseMappingArg(argparse.Action):
  """Takes a string argument and parse argument"""

  def __call__(self, parser, namespace, values, option_string):
    if values:
      if values[0] == '{' and values[-1] == '}':
        values = values[1:-1]
      if not isinstance(values, list):
        values = re.split('[ ,]', values)
      parsed_dict = getattr(namespace, self.dest, models.Parameter())
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


class ParseBundleSpec(argparse.Action):
  """Takes a string argument and parse argument"""

  def __call__(self, parser, namespace, values, option_string):
    if values:
      bundle_list = getattr(namespace, self.dest, List)
      for file_path in values:
        try:
          bundle_list += _load_bundles_spec(file_path.name)
        except ValueError:
          parser.error(
              f'argument {option_string} expected key:value, received {file_path}'
          )
    setattr(namespace, self.dest, bundle_list)


def expand_and_validate_path(arg) -> str:
  # Expand the path and check if it exists
  expanded_path = os.path.abspath(os.path.expanduser(arg))
  home_path = os.path.expanduser('~')
  # Cloud Shell only allows report downloads from paths in user's home
  # Check if the home directory is already present in the path if not
  if bool(os.getenv('CLOUD_SHELL')):
    # If default path append $HOME
    if arg == config.get('report_dir'):
      return os.path.join(home_path, expanded_path)
    # User supplied path
    elif home_path not in expanded_path:
      raise argparse.ArgumentTypeError(
          f'The {arg} folder must be located in your home directory')
  if not expanded_path or not os.path.exists(expanded_path):
    raise argparse.ArgumentTypeError(
        f"Dirctory '{arg}' does not exist. Create one mkdir -p {arg} and try again"
    )
  return expanded_path


def validate_args(args):
  if args.runbook is None and not args.bundle_spec:
    print(
        'Error: Provide a runbook id  or "--bundle-spec=YAML_FILE_PATH" must be provided.'
    )
    sys.exit(1)


class DeprecatedAction(argparse.Action):

  def __call__(self, parser, namespace, values, option_string=None):
    warnings.warn(f'Argument {option_string} is deprecated.',
                  DeprecationWarning)
    setattr(namespace, self.dest, values)


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

  parser.add_argument('--project',
                      action=DeprecatedAction,
                      metavar='P',
                      help=argparse.SUPPRESS)

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
      'runbook',
      help=
      'Runbook to execute in the format product/runbook-name or product/name',
      nargs='?')

  parser.add_argument('--bundle-spec',
                      nargs='*',
                      default=[],
                      action=ParseBundleSpec,
                      type=argparse.FileType('r'),
                      help='Path to YAML file containing bundle specifications')
  parser.add_argument(
      '-p',
      '--parameter',
      action=ParseMappingArg,
      nargs=1,
      default=models.Parameter(),
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
      '--report-dir',
      metavar='FILE',
      default=config.get('report_dir'),
      type=expand_and_validate_path,
      help=
      ('Specifies the full path to the directory where reports '
       'will be saved (default: /tmp/gcpdiag or in Cloud Shell $HOME/tmp/gcpdiag)'
      ))
  parser.add_argument(
      '--interface',
      metavar='FORMATTER',
      default=config.get('interface'),
      type=str,
      help=('What interface as one of [cli, api] (default: cli)'))

  parser.add_argument('--universe-domain',
                      type=str,
                      default=config.get('universe_domain'),
                      help='Domain name of APIs')

  return parser


def _validate_rule_pattern(runbook_name: str):
  runbook_name = runbook_name.lower()
  m = re.match(r'^([a-z]+)/([a-z\-]+)$', runbook_name)
  if not m:
    logging.error(
        'Invalid runbook name: %s should be `gcpdiag runbook product/runbook-id`',
        runbook_name)
    sys.exit(2)
  return runbook_name


def _load_runbook_rules(package: str):
  """Recursively import all submodules under a package, including subpackages."""
  if isinstance(package, str):
    pkg = importlib.import_module(package)
  for _, name, is_pkg in pkgutil.walk_packages(
      pkg.__path__,  # type: ignore
      pkg.__name__ + '.'):
    try:
      if name.endswith(('_test', 'output')):
        continue
      importlib.import_module(name)
    except ImportError as err:
      print(f"ERROR: can't import module: {err}", file=sys.stderr)
      continue
    if is_pkg:
      _load_runbook_rules(name)


def _load_bundles_spec(file_path):
  """Load step config from file

  Example:
    - bundle:
      parameter:
        project_id: "project_detail"
        zone: "location"
        ...
      steps:
        - gcpdiag.runbook.gce.generalized_steps.VmLifecycleState
        - gcpdiag.runbook.gce.ops_agent.VmHasAServiceAccount
        - gcpdiag.runbook.gce.ssh.PoxisUserHasValidSshKeyCheck
    - bundle:
      ...
  """
  if file_path:
    # Read the file contents
    if os.path.exists(file_path):
      with open(file_path, encoding='utf-8') as f:
        content = f.read()
    else:
      print(f'ERROR: Bundle Specification file: {file_path} does not exist!',
            file=sys.stderr)
      sys.exit(1)

    # Parse the content of the file as YAML
    if content:
      try:
        parsed_content = yaml.safe_load(content)
        return parsed_content
      except yaml.YAMLError as err:
        print(f"ERROR: can't parse content of the file as YAML: {err}",
              file=sys.stderr)
        sys.exit(1)


def _initialize_output():
  constructor = terminal_output.TerminalOutput
  kwargs = {
      'log_info_for_progress_only': (config.get('verbose') == 0),
  }
  if config.get('interface') == 'cli':
    output = constructor(**kwargs)
    return output
  elif config.get('interface') == 'api':
    raise NotImplementedError
  else:
    output = constructor(**kwargs)
  # default to terminal
  return output


def run_and_get_report(argv=None, credentials: str = None) -> dict:
  # Initialize argument parser
  parser = _init_runbook_args_parser()
  args = parser.parse_args(argv[1:])

  if credentials:
    apis.set_credentials(credentials)

  # Allow to change defaults using a hook function.
  hooks.set_lint_args_hook(args)

  # Initialize configuration
  config.init(vars(args), terminal_output.is_cloud_shell())

  # Initialize Repository, and Tests.
  dt_engine = runbook.DiagnosticEngine()
  _load_runbook_rules(runbook.__name__)

  # ^^^ If you add gcpdiag/runbook/[NEW-PRODUCT] directory, update also
  # pyinstaller/hook-gcpdiag.runbook.py and bin/precommit-required-files

  # Initialize proper output formater
  output = _initialize_output()
  dt_engine.interface.output = output
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

  # for capatibility till --project is fully deprecated under runbooks
  if args.project and args.project.isdigit():
    args.parameter['project_number'] = args.project
  elif args.project and not args.project.isdigit():
    args.parameter['project_id'] = args.project
  # Start the reporting
  output.display_banner()

  # Run the runbook or step connections.
  if args.runbook:
    # Rules name patterns that shall be included or excluded
    runbook_pattern = _validate_rule_pattern(args.runbook)
    output.display_header()
    tree = dt_engine.load_tree(runbook_pattern)
    if not callable(tree):
      logging.error('Can\'t instantiate Runbook')
      sys.exit(2)
    dt_engine.add_task((tree(), args.parameter))
  elif args.bundle_spec:
    for bundle in args.bundle_spec:
      bundle = dt_engine.load_steps(parameter=bundle['parameter'],
                                    steps_to_run=bundle['steps'])
      dt_engine.add_task((bundle, bundle.parameter))

  dt_engine.run()
  output.display_footer(dt_engine.interface.rm)

  # Clean up the kubeconfig file generated for gcpdiag
  kubectl.clean_up()

  report = {}
  report['version'] = config.VERSION
  report['reports'] = dt_engine.interface.rm.generate_reports()
  return report


def run(argv) -> None:
  run_and_get_report(argv)
