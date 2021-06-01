# Lint as: python3
"""GKE nodes service account permissions for logging.

The service account used by GKE nodes should have the logging.logWriter
role, otherwise ingestion of logs won't work.
"""

from gcp_doctor import lint, models
from gcp_doctor.queries import gke, iam

ROLE = 'roles/logging.logWriter'


def prefetch_rule(context: models.Context):
  # Make sure that we have the IAM policy in cache.
  project_ids = {c.project_id for c in gke.get_clusters(context).values()}
  for pid in project_ids:
    iam.get_project_policy(pid)


def run_rule(context: models.Context, report: lint.LintReportRuleInterface):
  # Find all clusters with logging enabled.
  clusters = gke.get_clusters(context)
  if not clusters:
    report.add_skipped(None, 'no clusters found')
  for _, c in sorted(clusters.items()):
    if not c.has_logging_enabled():
      report.add_skipped(c, 'logging disabled')
    else:
      iam_policy = iam.get_project_policy(c.project_id)
      # Verify service-account permissions for every nodepool.
      for np in c.nodepools:
        sa = np.service_account
        if not iam_policy.has_role_permissions(f'serviceAccount:{sa}', ROLE):
          report.add_failed(np, f'service account: {sa}\nmissing role: {ROLE}')
        else:
          report.add_ok(np)
