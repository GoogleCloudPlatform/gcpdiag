# Lint as: python3
"""GKE nodepools have the required permissions for logging and monitoring.

The service account used by GKE nodes should have the following roles,
otherwise ingestion of metrics and logs won't work: monitoring.metricWriter,
logging.logWriter.
"""

from gcp_doctor import lint, models
from gcp_doctor.queries import gke, iam


def run_test(context: models.Context, report: lint.LintReportTestInterface):
  """Run lint test in this context and report findings."""

  # find all clusters with monitoring enabled
  clusters = gke.get_clusters(context)
  for _, c in sorted(clusters.items()):
    if not c.has_logging_enabled():
      report.add_skipped(c, 'monitoring disabled')
    else:
      iam_policy = iam.get_project_policy(c.project_id)
      # verify service-account permissions for every nodepool
      for np in c.nodepools:
        sa = np.service_account
        missing_roles = [
            role for role in [
                'roles/monitoring.viewer', 'roles/monitoring.metricWriter',
                'roles/logging.logWriter'
            ]
            if not iam_policy.has_role_permissions(f'serviceAccount:{sa}', role)
        ]
        if missing_roles:
          report.add_failed(np, 'missing roles: ' + ', '.join(missing_roles))
        else:
          report.add_ok(np)
