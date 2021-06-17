# Lint as: python3
"""Service Account used by the cluster exists and not disabled

Disabling or deleting service account used by the nodepool will render
this nodepool not functional. To fix - restore the default compute account
or service account that was specified when nodepool was created.
"""

from gcp_doctor import lint, models
from gcp_doctor.queries import gke, iam


def run_rule(context: models.Context, report: lint.LintReportRuleInterface):
  # Find all clusters.
  clusters = gke.get_clusters(context)
  if not clusters:
    report.add_skipped(None, 'no clusters found')
  for _, c in sorted(clusters.items()):
    # Verify service-account exists for every nodepool.
    for np in c.nodepools:
      sa = np.service_account

      # TODO: this may not work for cross-project service accounts
      accounts = iam.get_service_accounts(context)
      if sa in iam.get_service_accounts(context):
        service_account = accounts[sa]
        if service_account.disabled:
          report.add_failed(np, f'service account: {sa}\n is disabled')
      else:
        if np.has_default_service_account():
          report.add_failed(np,
                            f'default service account: {sa}\n does not exists')
        else:
          report.add_failed(np, f'service account: {sa}\n does not exists')
      report.add_ok(np)
