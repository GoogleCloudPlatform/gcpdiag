# Lint as: python3
"""Enable http load balancing on clusters to use GKE ingress and container-native load balancing.

If this is disabled GKE ingresses will be stuck in the creating state. Similarly if
this is disabled after GKE ingresses have been created but before they are deleted the GKE ingresses
will be stuck in the deleting state.
"""

from gcpdiag import lint, models
from gcpdiag.queries import gke


def run_rule(context: models.Context, report: lint.LintReportRuleInterface):
  clusters = gke.get_clusters(context)
  if not clusters:
    report.add_skipped(None, 'no clusters found')
  for _, c in sorted(clusters.items()):
    if not c.has_http_load_balancing_enabled():
      report.add_failed(c)
    else:
      report.add_ok(c)
