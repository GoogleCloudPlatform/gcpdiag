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

# Note that we don't have a general rule that checks this for all products,
# because the grant is done lazily, as soon as it is needed. So check that the
# grant is there only when resources of a certain product (like GKE clusters)
# are present, and we know that the grant is necessary for the correct
# operation of that product. Copy the rule for other products, as necessary.
"""Google APIs service agent has Editor role.

The Google API service agent project-number@cloudservices.gserviceaccount.com
runs internal Google processes on your behalf. It is automatically granted the
Editor role on the project.

Reference: https://cloud.google.com/iam/docs/service-accounts#google-managed
"""

from gcpdiag import lint, models
from gcpdiag.queries import crm, gce, iam

ROLE = 'roles/editor'


def prefetch_rule(context: models.Context):
  # Make sure that we have the IAM policy in cache.
  project_ids = {i.project_id for i in gce.get_instances(context).values()}
  for pid in project_ids:
    iam.get_project_policy(pid)


def run_rule(context: models.Context, report: lint.LintReportRuleInterface):
  instances = gce.get_instances(context)
  if not instances:
    report.add_skipped(None, 'no instances found')
    return

  for project_id in sorted({i.project_id for i in instances.values()}):
    project = crm.get_project(project_id)
    sa_email = f'{project.number}@cloudservices.gserviceaccount.com'
    iam_policy = iam.get_project_policy(project_id)
    if not iam_policy.has_role_permissions(f'serviceAccount:{sa_email}', ROLE):
      report.add_failed(project,
                        f'service account: {sa_email}\nmissing role: {ROLE}')
    else:
      report.add_ok(project)
