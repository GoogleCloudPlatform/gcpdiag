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
"""Dataflow service account has dataflow.serviceAgent role

Check that the service account
service-<project-number>@dataflow-service-producer-prod.iam.gserviceaccount.com
has the following role: roles/dataflow.serviceAgent
"""

from gcpdiag import lint, models
from gcpdiag.queries import crm, iam


def prefetch_rule(context: models.Context):
  # Make sure that we have the IAM policy in cache.
  iam.get_project_policy(context)


def run_rule(context: models.Context, report: lint.LintReportRuleInterface):

  role = 'roles/dataflow.serviceAgent'

  project = crm.get_project(context.project_id)
  iam_policy = iam.get_project_policy(context)

  project_nr = crm.get_project(context.project_id).number

  for member in sorted(iam_policy.get_members()):
    if member.startswith(
        'serviceAccount:service-' + str(project_nr) +
        '@dataflow-service-producer-prod.iam.gserviceaccount.com'):

      if iam_policy.has_role_permissions(member, role):
        report.add_ok(project)
        break
      else:
        report.add_failed(project, member + f' does not has the role {role}')
