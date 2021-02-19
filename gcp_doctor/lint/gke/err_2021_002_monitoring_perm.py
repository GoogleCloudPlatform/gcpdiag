# Lint as: python3
"""GKE nodes service account permissions for monitoring.

The service account used by GKE nodes should have the monitoring.metricWriter
role, otherwise ingestion of metrics won't work.
"""

from gcp_doctor import lint, models
from gcp_doctor.queries import gke, iam

ROLE = 'roles/monitoring.metricWriter'


def run_test(context: models.Context, report: lint.LintReportTestInterface):
  # Find all clusters with monitoring enabled.
  clusters = gke.get_clusters(context)
  if not clusters:
    report.add_skipped(None, 'no clusters found')
  for _, c in sorted(clusters.items()):
    if not c.has_monitoring_enabled():
      report.add_skipped(c, 'monitoring disabled')
    else:
      iam_policy = iam.get_project_policy(c.project_id)
      # Verify service-account permissions for every nodepool.
      for np in c.nodepools:
        sa = np.service_account
        if not iam_policy.has_role_permissions(f'serviceAccount:{sa}', ROLE):
          report.add_failed(np, f'service account: {sa}\nmissing role: {ROLE}')
        else:
          report.add_ok(np)
