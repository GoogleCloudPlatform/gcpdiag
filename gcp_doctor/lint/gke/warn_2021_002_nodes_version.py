# Lint as: python3
"""GKE nodes version available for new clusters.

The GKE nodes version should be a version that is available
for new clusters. If a version is not available it could mean
that it is deprecated, or possibly retired due to issues with
it.
"""

from gcp_doctor import lint, models
from gcp_doctor.queries import gke


def run_rule(context: models.Context, report: lint.LintReportRuleInterface):
  clusters = gke.get_clusters(context)
  if not clusters:
    report.add_skipped(None, 'no clusters found')
  for _, c in sorted(clusters.items()):
    valid_node_versions = gke.get_valid_node_versions(c.project_id, c.location)
    for np in c.nodepools:
      if np.version not in valid_node_versions:
        report.add_failed(np,
                          'valid versions: ' + ', '.join(valid_node_versions),
                          np.version)
      else:
        report.add_ok(np, np.version)
