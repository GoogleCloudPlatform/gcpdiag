# Lint as: python3
"""GKE node service account has the required permissions for logging and monitoring.

The service account used by GKE nodes should have the following roles,
otherwise ingestion of metrics and logs won't work: monitoring.metricWriter,
logging.logWriter.
"""

from gcp_doctor import models
from gcp_doctor.lint import lint
from gcp_doctor.queries import gke, iam


def run_test(context: models.Context) -> lint.LintFindings:
  """Run lint test in this context and report findings."""
  findings = lint.LintFindings()

  # find all clusters with monitoring enabled
  clusters = gke.get_clusters(context)
  for c in clusters:
    if not c.has_monitoring_enabled():
      findings.add_skipped(c, 'monitoring disabled')
    else:
      iam_policy = iam.ProjectPolicy(c.project)
      # verify service-account permissions for every nodepool
      for np in c.nodepools:
        sa = np.service_account
        missing_roles = [
            role for role in [
                'monitoring.viewer', 'monitoring.metricWriter',
                'logging.logWriter'
            ]
            if not iam_policy.has_role_permissions(f'serviceAccount:{sa}', role)
        ]
        if not missing_roles:
          findings.add_failed(np, 'missing roles' + ' '.join(missing_roles))
        else:
          findings.add_ok(np)
  return findings
