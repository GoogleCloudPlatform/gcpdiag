"""DNS logging is enabled for public zones.

If not enabled, customers wouldn't have visbility to what queries are being made to the zone.
"""

from gcpdiag import lint, models
from gcpdiag.queries import network


def run_rule(context: models.Context, report: lint.LintReportRuleInterface):
  #  project = crm.get_project(context.project_id)
  zones = network.get_zones(context.project_id)
  if not zones:
    report.add_skipped(None, 'no zones found')
    return
  for c in zones:
    if (c.is_public and not c.cloud_logging_config):
      report.add_failed(c, None, ' logging is disabled for this public zone')
    else:
      report.add_ok(c)
