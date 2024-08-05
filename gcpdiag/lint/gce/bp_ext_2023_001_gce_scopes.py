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

# Lint as: python3
"""GCE Instances follows access scope best practice

Google recommends not to rely on access scopes but instead set the cloud-platform access
scope and control the service account access by granting fine-grained IAM roles.
Enabling a custom service account with very coarse-grained permissions
and a very restricted access scope will ensure the connection
to or from the VM is limited and implements a security-in-depth strategy where multiple
layers of security are used for holistic protection.
"""

import operator as op

from gcpdiag import lint, models
from gcpdiag.queries import crm, gce, iam


def run_rule(context: models.Context, report: lint.LintReportRuleInterface):

  #Fetching the list of instances and declaring an IAM policy object
  instances = gce.get_instances(context)
  iam_policy = iam.get_project_policy(context.project_id)
  project_number = crm.get_project(context.project_id).number
  cloud_platform_scope = "https://www.googleapis.com/auth/cloud-platform"

  #Defining list of pre-defined roles that a default SA must not have
  roles = ["roles/editor", "roles/owner", "roles/viewer", "roles/browser"]

  if not instances:
    report.add_skipped(None, "no instances found")
    return

  for i in sorted(instances.values(),
                  key=op.attrgetter("project_id", "full_path")):
    service_account = f"serviceAccount:{i.service_account}"
    basic_roles_granted = [
        iam_policy.has_role_permissions(service_account, role) for role in roles
    ]
    # GKE nodes are not checked by this rule
    if i.is_gke_node():
      continue

    if (cloud_platform_scope in i.access_scopes) and any(basic_roles_granted):
      report.add_failed(
          i,
          f"{i.service_account} has a basic role granted along with cloud-platform scope."
      )

    elif any(basic_roles_granted):
      report.add_failed(i, f"{i.service_account} has a basic role granted.")

    elif (f"{project_number}-compute@developer.gserviceaccount.com"
          not in service_account) and not any(basic_roles_granted):
      report.add_ok(i)
