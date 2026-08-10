# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""GKE credentials and certificate authority are fully rotated and valid.

GKE clusters require periodic credential rotation to ensure the Certificate
Authority certificates are rotated before they expire. Running clusters with
old certificates (older than 30 days) or incomplete rotations increases
security risks and could lead to cluster unrecoverability if they expire.
"""

import datetime

from gcpdiag import lint, models
from gcpdiag.queries import gke


def _get_now() -> datetime.datetime:
  return datetime.datetime.now(datetime.timezone.utc)


def run_rule(context: models.Context, report: lint.LintReportRuleInterface) -> None:
  clusters = gke.get_clusters(context)
  if not clusters:
    report.add_skipped(None, 'no clusters found')
    return

  for _, c in sorted(clusters.items()):
    cert_info = c.cluster_ca_certificate_info
    if not cert_info:
      report.add_skipped(c, 'cluster CA certificate is not available or not parseable')
      continue

    try:
      now = _get_now()
      certs_list = cert_info['certificates']
      expiry_dates = [datetime.datetime.fromisoformat(cert['notAfter']) for cert in certs_list]
      earliest_expiry_date = min(expiry_dates)
      remaining_days = (earliest_expiry_date - now).days
      expiry_date_str = earliest_expiry_date.strftime('%Y-%m-%d')

      if len(certs_list) > 1:
        report.add_failed(
          c,
          reason=(
            'Credential rotation has been initiated but is not fully'
            ' completed (multiple CA certificates found in trust bundle).'
          ),
          short_info=(
            f'Rotation incomplete; oldest cert valid for {remaining_days}'
            f' more days (expires on {expiry_date_str})'
          ),
        )
      elif remaining_days <= 30:
        report.add_failed(
          c,
          reason=('Certificate rotation is incomplete or certificate expires within 30 days'),
          short_info=(
            f'Certificate is valid for {remaining_days} more days (expires on {expiry_date_str})'
          ),
        )
      else:
        report.add_ok(
          c,
          short_info=(
            f'Certificate is valid for {remaining_days} more days (expires on {expiry_date_str})'
          ),
        )
    except (KeyError, ValueError) as err:
      report.add_skipped(c, f'failed to process cluster CA certificate: {err}')
      continue
