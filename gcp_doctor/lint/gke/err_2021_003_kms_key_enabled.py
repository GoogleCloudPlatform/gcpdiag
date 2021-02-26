# Lint as: python3
"""App-layer secrets encryption is activated and Cloud KMS key is enabled.

GKE's default service account cannot use a disabled Cloud KMS key for
application-level secrets encryption.
"""

from gcp_doctor import lint, models
from gcp_doctor.queries import gke, kms


def run_test(context: models.Context, report: lint.LintReportTestInterface):
  clusters = gke.get_clusters(context)
  if not clusters:
    report.add_skipped(None, 'no clusters found')
  for _, c in sorted(clusters.items()):
    if not c.has_app_layer_enc_enabled():
      report.add_skipped(c, 'App-layer secrets encryption isn\'t enabled')
    else:
      crypto_key = kms.get_crypto_key(c.app_layer_sec_key)
      if crypto_key.is_destroyed():
        report.add_failed(c, f'Key {crypto_key} is destroyed')
      elif not crypto_key.is_enabled():
        report.add_failed(c, f'Key {crypto_key} is disabled')
      else:
        report.add_ok(c)
