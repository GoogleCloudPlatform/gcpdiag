"""DNSSEC is enabled for public zones.

It is recommended to enable DNSSEC for public zones.
"""

from gcpdiag import lint, models
from gcpdiag.queries import network


def run_rule(context: models.Context, report: lint.LintReportRuleInterface):
  zones = network.get_zones(context.project_id)
  if not zones:
    report.add_skipped(None, 'no zones found')
    return
  for c in zones:
    if (c.is_public and not c.dnssec_config_state):
      report.add_failed(c, None, ' DNSSEC is disabled for this public zone')
    else:
      report.add_ok(c)
