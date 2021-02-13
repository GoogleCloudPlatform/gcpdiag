# Lint as: python3
"""gcp-doctor lint command."""

import argparse
import logging

from gcp_doctor import lint, models
from gcp_doctor.lint import gke, report_terminal
from gcp_doctor.queries import apis


def run(argv):
  del argv
  parser = argparse.ArgumentParser(
      description='Run diagnostics in GCP projects.')
  parser.add_argument('--project',
                      action='append',
                      required=True,
                      help='Project ID (can be specified multiple times)')
  args = parser.parse_args()

  # Initialize Context, Repository, and Tests
  context = models.Context(projects=args.project)
  repo = lint.LintTestRepository()
  repo.load_tests(gke.__path__, gke.__name__)
  report = report_terminal.LintReportTerminal()

  # Logging setup.
  logging_handler = report.get_logging_handler()
  logger = logging.getLogger()
  logger.addHandler(logging_handler)
  logger.setLevel(logging.INFO)

  # Run the tests.
  apis.login()
  report.lint_start(context)
  repo.run_tests(context, report)
