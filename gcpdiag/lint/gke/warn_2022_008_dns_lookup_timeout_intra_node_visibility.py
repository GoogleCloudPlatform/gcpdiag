# Copyright 2022 Google LLC
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

###
"""GKE connectivity: possible dns timeout in some gke versions.

Some GKE versions (starting with 1.18.16-gke.300) have DNS timeout issues
when intranode visibility is enabled and
if the client Pod and kube-dns Pod are located on the same node.
See: https://cloud.google.com/kubernetes-engine/docs/how-to/intranode-visibility#dns_timeouts
"""

from gcpdiag import lint, models
from gcpdiag.queries import gke


def run_rule(context: models.Context, report: lint.LintReportRuleInterface):
  clusters = gke.get_clusters(context)
  if not clusters:
    report.add_skipped(None, 'no clusters found')

  for _, cluster in sorted(clusters.items()):
    guarded_for_unaffected_versions = _guard_for_unaffected_versions(
        cluster, report)
    if guarded_for_unaffected_versions:
      continue

    _check_for_affected_version(cluster, report)


def _guard_for_unaffected_versions(
    cluster: gke.Cluster, report: lint.LintReportRuleInterface) -> bool:
  if not cluster.has_intra_node_visibility_enabled():
    report.add_ok(cluster, 'intra node visibility disabled -> unaffected')
    return True
  elif cluster.master_version.major != 1:
    report.add_ok(cluster, 'gke major version != 1 unaffected')
    return True
  elif cluster.master_version.minor >= 23:
    report.add_ok(cluster, 'gke version >= 1.23 unaffected')
    return True
  else:
    return False


def _check_for_affected_version(cluster: gke.Cluster,
                                report: lint.LintReportRuleInterface):
  if (cluster.master_version.minor == 18 and
      cluster.master_version.minor >= 16):
    report.add_failed(
        cluster,
        'gke version ' + cluster.master_version.version_str + ' is affected')
  elif (cluster.master_version.minor == 19 and
        cluster.master_version.patch >= 7 and
        cluster.master_version.patch < 16):
    report.add_failed(
        cluster,
        'gke version ' + cluster.master_version.version_str + ' is affected')
  elif (cluster.master_version.minor == 20 and
        cluster.master_version.patch >= 2 and
        cluster.master_version.patch < 13):
    report.add_failed(
        cluster,
        'gke version ' + cluster.master_version.version_str + ' is affected')
  elif (cluster.master_version.minor == 21 and
        cluster.master_version.patch < 5):
    report.add_failed(
        cluster,
        'gke version ' + cluster.master_version.version_str + ' is affected')
  elif (cluster.master_version.minor == 22 and
        cluster.master_version.patch < 2):
    report.add_failed(
        cluster,
        'gke version ' + cluster.master_version.version_str + ' is affected')
  else:
    report.add_ok(cluster, 'no affected version detected')
