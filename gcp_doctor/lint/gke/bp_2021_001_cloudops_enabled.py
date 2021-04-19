# Lint as: python3
"""GKE system logging and monitoring enabled.

Disabling system logging and monitoring (aka "GKE Cloud Operations") severly
impacts the ability of Google Cloud Support to troubleshoot any issues that
you might have.
"""

from gcp_doctor import lint, models
from gcp_doctor.queries import gke


def run_rule(context: models.Context, report: lint.LintReportRuleInterface):
  clusters = gke.get_clusters(context)
  if not clusters:
    report.add_skipped(None, 'no clusters found')
  for _, c in sorted(clusters.items()):
    disabled = []
    if not c.has_logging_enabled():
      disabled.append('logging')
    if not c.has_monitoring_enabled():
      disabled.append('monitoring')
    if disabled:
      report.add_failed(c, ' and '.join(disabled) + ' are disabled')
    else:
      report.add_ok(c)
