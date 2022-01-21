# Lint as: python3
"""Cloud Monitoring agent is enabled.

Memory and disk usage metrics are often useful when troubleshooting,
however, the Cloud Monitoring agent is not enabled by default when
when a cluster is created.
"""

from gcpdiag import lint, models
from gcpdiag.queries import dataproc


def run_rule(context: models.Context, report: lint.LintReportRuleInterface):
  clusters = dataproc.get_clusters(context)
  if not clusters:
    report.add_skipped(None, 'no dataproc clusters found')
  else:
    for cluster in clusters:
      if cluster.is_stackdriver_monitoring_enabled():
        report.add_ok(cluster)
      else:
        report.add_failed(cluster)
