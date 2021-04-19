# Lint as: python3
"""GKE master version available for new clusters.

The GKE master version should be a version that is available
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
    valid_master_versions = gke.get_valid_master_versions(
        c.project_id, c.location)
    if c.master_version not in valid_master_versions:
      report.add_failed(c,
                        'valid versions: ' + ', '.join(valid_master_versions),
                        c.master_version)
    else:
      report.add_ok(c, c.master_version)
