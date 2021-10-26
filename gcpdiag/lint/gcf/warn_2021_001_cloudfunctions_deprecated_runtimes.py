# Lint as: python3
"""Cloud Functions don't use deprecated runtimes.

Nodejs8 and Go111 runtimes are deprecated.
"""

from gcpdiag import lint, models
from gcpdiag.queries import gcf


def run_rule(context: models.Context, report: lint.LintReportRuleInterface):
  cloudfunctions = gcf.get_cloudfunctions(context)
  if not cloudfunctions:
    report.add_skipped(None, 'no functions found')
  for _, cloudfunction in sorted(cloudfunctions.items()):
    if cloudfunction.runtime in ['go111', 'nodejs8']:
      report.add_failed(
          cloudfunction,
          f'cloudfunction with deprecated runtime {cloudfunction.runtime}')
    else:
      report.add_ok(cloudfunction)
