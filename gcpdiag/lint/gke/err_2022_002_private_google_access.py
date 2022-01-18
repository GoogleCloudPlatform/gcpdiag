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
"""GKE nodes of private clusters can access Google APIs and services.

Private GKE clusters must have Private Google Access enabled on the subnet where
cluster is deployed.
"""
from gcpdiag import lint, models
from gcpdiag.queries import gke, network


def run_rule(context: models.Context, report: lint.LintReportRuleInterface):
  clusters = gke.get_clusters(context)
  if not clusters:
    report.add_skipped(None, 'no clusters found')
  for _, c in sorted(clusters.items()):
    if c.is_private and not c.subnetwork.is_private_ip_google_access():

      router = network.get_router(project_id=context.project_id,
                                  region=c.subnetwork.region,
                                  network=c.network)

      if router.subnet_has_nat(c.subnetwork):
        # Cloud NAT configured for subnet
        report.add_ok(c)
      else:
        # no Cloud NAT configured for subnet
        report.add_failed(c, (f' subnet {c.subnetwork.name} has'
                              ' Private Google Access disabled and Cloud NAT'
                              ' is not available'))
    else:
      report.add_ok(c)
