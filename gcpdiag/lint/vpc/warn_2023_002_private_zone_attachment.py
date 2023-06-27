"""Private zone is attached to a VPC.

If not attached to a VPC, Private zones will not be usable.
"""

from gcpdiag import lint, models
from gcpdiag.queries import network


def run_rule(context: models.Context, report: lint.LintReportRuleInterface):
  zones = network.get_zones(context.project_id)
  if not zones:
    report.add_skipped(None, 'no zones found')
    return
  for c in zones:
    if (not c.is_public and not c.vpc_attached):
      report.add_failed(c, None, ' Private zone that is not attached to a VPC')
    else:
      report.add_ok(c)
