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
"""GKE service account permissions.

Verify that the Google Kubernetes Engine service account exists and has
the Kubernetes Engine Service Agent role on the project.
"""
from gcpdiag import lint, models
from gcpdiag.queries import crm, gce, iam

# defining role
ROLE = 'roles/container.serviceAgent'


# creating rule to report if default SA exists
def run_rule(context: models.Context, report: lint.LintReportRuleInterface):
  instances = gce.get_instances(context)
  if not instances:
    report.add_skipped(None, 'no instances found')
  project_ids = {i.project_id for i in instances.values()}
  for i in project_ids:
    # fetch project number
    project = crm.get_project(i)
    sa = 'service-{}@container-engine-robot.iam.gserviceaccount.com'.format(
        project.number)
    # get iam policy
    iam_policy = iam.get_project_policy(i)
    if iam_policy.has_role_permissions(f'serviceAccount:{sa}', ROLE):
      report.add_ok(project)
    else:
      report.add_failed(project,
                        reason=f'service account: {sa}\nmissing role: {ROLE}')
