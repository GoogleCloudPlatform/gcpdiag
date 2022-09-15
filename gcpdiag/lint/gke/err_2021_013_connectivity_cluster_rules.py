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
"""GKE cluster firewall rules are configured.

GKE automatically creates firewall rules for cluster
communication. We verify that the VPC firewall rules
are present.
"""

# Note that this rule is separate from the other rules that
# do the connectivity check so that it can be excluded more
# easily if somebody takes into account that the automatic
# rule creation fails, but provisions the firewall on their own.

from gcpdiag import lint, models
from gcpdiag.queries import gke


def _run_rule_cluster(report: lint.LintReportRuleInterface, c: gke.Cluster):
  try:
    cluster_fw_rules_names = [
        f'gke-{c.name}-{c.cluster_hash}-vms',
        f'gke-{c.name}-{c.cluster_hash}-all',
    ]
    if c.is_private:
      cluster_fw_rules_names.append(f'gke-{c.name}-{c.cluster_hash}-master')

    missing_rules = [
        rule_name for rule_name in cluster_fw_rules_names \
            if not c.network.firewall.verify_ingress_rule_exists(rule_name)
        ]
    if missing_rules:
      report.add_failed(c,
                        'missing firewall rules: ' + ', '.join(missing_rules))
    else:
      report.add_ok(c)
  except gke.UndefinedClusterPropertyError as err:
    report.add_skipped(c, str(err))


def run_rule(context: models.Context, report: lint.LintReportRuleInterface):
  clusters = gke.get_clusters(context)
  if not clusters:
    report.add_skipped(None, 'no clusters found')
    return

  for _, c in sorted(clusters.items()):
    _run_rule_cluster(report, c)
