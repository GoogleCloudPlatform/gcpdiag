# Lint as: python3
"""gcp-doctor lint command."""

import argparse
import logging
import sys

from gcp_doctor import config, lint, models, utils
from gcp_doctor.lint import gce, gke, report_terminal
from gcp_doctor.queries import apis, project


def run(argv) -> int:
  del argv
  parser = argparse.ArgumentParser(
      description='Run diagnostics in GCP projects.')

  parser.add_argument('--project',
                      action='append',
                      metavar='P',
                      required=True,
                      help='Project ID (can be specified multiple times)')

  parser.add_argument('--show-skipped',
                      help='Show skipped rules',
                      action='store_true',
                      default=False)

  parser.add_argument('--hide-skipped',
                      help=argparse.SUPPRESS,
                      action='store_false',
                      dest='show_skipped')

  parser.add_argument('--hide-ok',
                      help='Hide rules with result OK',
                      action='store_true',
                      default=False)

  parser.add_argument('--show-ok',
                      help=argparse.SUPPRESS,
                      action='store_false',
                      dest='hide_skipped')

  parser.add_argument('-v',
                      '--verbose',
                      action='count',
                      default=0,
                      help='Increase log verbosity')

  parser.add_argument(
      '--within-days',
      metavar='D',
      type=int,
      help=
      f'How far back to search logs and metrics (default: {config.WITHIN_DAYS})',
      default=config.WITHIN_DAYS)

  args = parser.parse_args()

  # Initialize configuration
  config.WITHIN_DAYS = args.within_days

  # Initialize Context, Repository, and Tests.
  context = models.Context(projects=args.project)
  repo = lint.LintRuleRepository()
  repo.load_rules(gce)
  repo.load_rules(gke)
  report = report_terminal.LintReportTerminal(
      log_info_for_progress_only=(args.verbose == 0),
      show_ok=not args.hide_ok,
      show_skipped=args.show_skipped)

  # Verify that we have access.
  for project_id in context.projects:
    try:
      project.get_project(project_id)
    except utils.GcpApiError:
      print(
          f"ERROR: can't access project: {project_id}. Please verify that you have Viewer access.",
          file=sys.stdout)
      sys.exit(1)

  # Logging setup.
  logging_handler = report.get_logging_handler()
  logger = logging.getLogger()
  # Make sure we are only using our own handler
  logger.handlers = []
  logger.addHandler(logging_handler)
  if args.verbose >= 2:
    logger.setLevel(logging.DEBUG)
  else:
    logger.setLevel(logging.INFO)

  # Run the tests.
  report.banner()
  apis.login()
  report.lint_start(context)
  exit_code = repo.run_rules(context, report)

  # (google internal) Report usage information.
  details = {
      str(k): v['overall_status'] for k, v in report.rules_report.items()
  }
  utils.report_usage_if_running_at_google('lint', details)

  # Exit 0 if there are no failed rules.
  sys.exit(exit_code)
