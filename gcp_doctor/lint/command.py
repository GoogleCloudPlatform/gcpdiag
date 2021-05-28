# Lint as: python3
"""gcp-doctor lint command."""

import argparse
import logging
import sys

from gcp_doctor import lint, models, utils
from gcp_doctor.lint import gce, gke, report_terminal
from gcp_doctor.queries import apis


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
                      help='Show skipped rules',
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

  args = parser.parse_args()

  # Initialize Context, Repository, and Tests.
  context = models.Context(projects=args.project)
  repo = lint.LintRuleRepository()
  repo.load_rules(gce)
  repo.load_rules(gke)
  report = report_terminal.LintReportTerminal(
      log_info_for_progress_only=(args.verbose == 0),
      show_ok=not args.hide_ok,
      show_skipped=args.show_skipped)

  # Logging setup.
  logging_handler = report.get_logging_handler()
  logger = logging.getLogger()
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
