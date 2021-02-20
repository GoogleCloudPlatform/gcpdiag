# Lint as: python3
"""gcp-doctor lint command."""

import argparse
import logging

from gcp_doctor import lint, models
from gcp_doctor.lint import gce, gke, report_terminal
from gcp_doctor.queries import apis


def run(argv):
  del argv
  parser = argparse.ArgumentParser(
      description='Run diagnostics in GCP projects.')
  parser.add_argument('--project',
                      action='append',
                      metavar='P',
                      required=True,
                      help='Project ID (can be specified multiple times)')
  parser.add_argument('-v',
                      '--verbose',
                      action='count',
                      default=0,
                      help='Increase log verbosity')
  args = parser.parse_args()

  # Initialize Context, Repository, and Tests
  context = models.Context(projects=args.project)
  repo = lint.LintTestRepository()
  repo.load_tests(gce.__path__, gce.__name__)
  repo.load_tests(gke.__path__, gke.__name__)
  report = report_terminal.LintReportTerminal(
      log_info_for_progress_only=(args.verbose == 0))

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
  repo.run_tests(context, report)
