# Copyright 2021 Google LLC
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
"""App-layer secrets encryption is activated and Cloud KMS key is enabled.

GKE's default service account cannot use a disabled or destroyed Cloud KMS key
for application-level secrets encryption.
"""

from gcpdiag import lint, models
from gcpdiag.queries import gke, kms


def run_rule(context: models.Context, report: lint.LintReportRuleInterface):
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
