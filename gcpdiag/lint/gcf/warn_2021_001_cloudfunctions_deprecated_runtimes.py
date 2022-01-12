# Lint as: python3
"""Cloud Functions don't use deprecated runtimes.

The following runtimes are deprecated: Nodejs8, Nodejs6, Go111.
"""

from gcpdiag import lint, models
from gcpdiag.queries import gcf


def run_rule(context: models.Context, report: lint.LintReportRuleInterface):
  cloudfunctions = gcf.get_cloudfunctions(context)
  if not cloudfunctions:
    report.add_skipped(None, 'no functions found')
  for cloudfunction in sorted(cloudfunctions.values(),
                              key=lambda cloudfunction: cloudfunction.name):
    if cloudfunction.runtime in ['go111', 'nodejs8', 'nodejs6']:
      report.add_failed(
          cloudfunction,
          f'cloudfunction with deprecated runtime {cloudfunction.runtime}')
    else:
      report.add_ok(cloudfunction)
