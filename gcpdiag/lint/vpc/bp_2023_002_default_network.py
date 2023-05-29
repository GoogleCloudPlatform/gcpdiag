"""Default VPC Network is present with auto-mode subnets.

If you need to modify the default route, then add explicit routes
for Google API destination IP ranges.

https://cloud.google.com/architecture/best-practices-vpc-design#custom-mode
"""

from gcpdiag import lint, models
from gcpdiag.queries import network


def run_rule(context: models.Context, report: lint.LintReportRuleInterface):

  networks = network.get_networks(context.project_id)
  if not networks:
    report.add_skipped(None, 'rule networks found')

  for networklist in networks:
    if networklist.name == 'default':
      if networklist.autosubnets:
        report.add_failed(networklist)
    else:
      report.add_ok(networklist)
