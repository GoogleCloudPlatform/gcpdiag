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
"""User has the required roles to create or modify scheduled queries.

Verify that the user trying to create or modify scheduled queries has the role
roles/bigquery.admin. If pub sub notification is configured, then user should
also have permission pubsub.topics.getIamPolicy which is part of the role
roles/pubsub.admin.
"""
from boltons.iterutils import get_path

from gcpdiag import lint, models
from gcpdiag.queries import apis, crm, logs

MATCH_STR = 'User not authorized to perform this action'

USER_NOT_AUTHORIZED = [
    'severity=ERROR',
    'protoPayload.@type="type.googleapis.com/google.cloud.audit.AuditLog"',
    f'protoPayload.status.message:("{MATCH_STR}")',
]
logs_by_project = {}


def prepare_rule(context: models.Context):
  logs_by_project[context.project_id] = logs.query(
      project_id=context.project_id,
      resource_type='audited_resource',
      log_name='log_id("cloudaudit.googleapis.com/activity")',
      filter_str=' AND '.join(USER_NOT_AUTHORIZED),
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
  useremail = ''
  pubsub = None
  if (logs_by_project.get(context.project_id) and
      logs_by_project[context.project_id].entries):
    for log_entry in logs_by_project[context.project_id].entries:
      if MATCH_STR in get_path(log_entry, ('protoPayload', 'status', 'message'),
                               default=''):
        useremail = get_path(
            log_entry,
            (
                'protoPayload',
                'authenticationInfo',
                'principalEmail',
            ),
        )

        pubsub = get_path(
            log_entry,
            (
                'protoPayload',
                'request',
                'transferConfig',
                'notificationPubsubTopic',
            ),
        )
        project_ok_flag = False

  if project_ok_flag:
    report.add_ok(project)
  elif project_ok_flag is False and pubsub is not None:
    report.add_failed(
        project,
        'User with principalEmail ' + useremail +
        ' does not have enough permissions to create or modify scheduled'
        ' queries with pub sub notifications.',
    )
  else:
    report.add_failed(
        project,
        'User with principalEmail ' + useremail +
        ' does not have enough permissions to create or modify scheduled'
        ' queries.',
    )
