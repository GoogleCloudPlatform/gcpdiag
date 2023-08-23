#
# Copyright 2022 Google LLC
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
"""An organization's policy doesn't block the BigQuery user domain.

There can be domain restriction policies applied to customer's organization.
The domain of the user that you are trying to share the BigQuery dataset with
should be present in the list of "Allowed" fields for the constraint
constraints/iam.allowedPolicyMemberDomains.
"""
from boltons.iterutils import get_path

from gcpdiag import lint, models
from gcpdiag.queries import apis, crm, logs

MATCH_STR = (
    'One or more users named in the policy do not belong to a permitted'
    ' customer')

POLICY_DO_NOT_BELONG_TO_USER_FILTER = [
    'severity=ERROR',
    'protoPayload.@type="type.googleapis.com/google.cloud.audit.AuditLog"',
    f'protoPayload.status.message:("{MATCH_STR}")',
]
logs_by_project = {}


def prepare_rule(context: models.Context):
  logs_by_project[context.project_id] = logs.query(
      project_id=context.project_id,
      resource_type='bigquery_dataset',
      log_name='log_id("cloudaudit.googleapis.com/activity")',
      filter_str=' AND '.join(POLICY_DO_NOT_BELONG_TO_USER_FILTER),
  )


def run_rule(context: models.Context, report: lint.LintReportRuleInterface):
  project = crm.get_project(context.project_id)
  # skip entire rule if logging disabled
  if not apis.is_enabled(context.project_id, 'logging'):
    report.add_skipped(project, 'Logging api is disabled')
    return
  if not apis.is_enabled(context.project_id, 'bigquery'):
    report.add_skipped(project, 'bigquery api is disabled')
    return
  project_ok_flag = True
  datasets = set()
  if (logs_by_project.get(context.project_id) and
      logs_by_project[context.project_id].entries):
    for log_entry in logs_by_project[context.project_id].entries:
      if MATCH_STR in get_path(log_entry, ('protoPayload', 'status', 'message'),
                               default=''):
        datasets.add(get_path(
            log_entry,
            (
                'protoPayload',
                'resourceName',
            ),
        ))
        project_ok_flag = False

  if project_ok_flag:
    report.add_ok(project)
  else:
    report.add_failed(
        project,
        """The following datasets cannot be shared with some users due to
'Domain restricted sharing' organization policy constraint: \n""" +
        '\n'.join(str(d) for d in datasets),
    )
