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
"""GKE service account permissions to manage project VPC firewall rules.

Verify that the Google Kubernetes Engine service account has the Compute Network
Admin role or custom role with sufficient fine-grained permissions to manage firewall rules
in the current or host project with Shared VPC.
"""

from gcpdiag import lint, models
from gcpdiag.queries import crm, gke, iam

# defining permissions
PERMISSIONS = [
    'compute.firewalls.create',
    'compute.firewalls.delete',
    'compute.firewalls.get',
    'compute.firewalls.list',
    'compute.firewalls.update',
    'compute.networks.updatePolicy',
]


def run_rule(context: models.Context, report: lint.LintReportRuleInterface):
  # Find all clusters.
  clusters = gke.get_clusters(context)
  if not clusters:
    report.add_skipped(None, 'no clusters found')
    return

  for _, c in sorted(clusters.items()):
    # fetch project number
    p: str = c.project_id
    project = crm.get_project(p)
    if c.project_id != c.network.project_id:
      # shared vpc
      p = c.network.project_id
    sa = (f'serviceAccount:service-{project.number}'
          '@container-engine-robot.iam.gserviceaccount.com')
    # get iam policy
    iam_policy = iam.get_project_policy(p)
    failed = False
    missing = []
    for permission in PERMISSIONS:
      if not iam_policy.has_permission(sa, permission):
        failed = True
        missing.append(permission)
    if failed:
      report.add_failed(c, (f'service account: {sa}\n'
                            f'VPC network: {c.network.short_path}\n'
                            f'missing permissions: {",".join(missing)})'))
    else:
      report.add_ok(c)
