#
# Copyright 2021 Google LLC
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
"""Dataflow worker service account has roles/dataflow.worker role

Check that the worker service account used in dataflow job
has the following role: roles/dataflow.worker role
"""

import itertools

from boltons.iterutils import get_path

from gcpdiag import lint, models
from gcpdiag.queries import apis, crm, iam, logs

# Criteria to filter for logs
LOG_FILTER = [
    'protoPayload.@type="type.googleapis.com/google.cloud.audit.AuditLog"',
    ('protoPayload.methodName="dataflow.jobs.updateContents" OR'
     ' "dataflow.jobs.create"'),
]
logs_by_project = {}
policies_by_project = {}

WORKER_ROLE = 'roles/dataflow.worker'
EDITOR_ROLE = 'roles/editor'
OWNER_ROLE = 'roles/owner'


def prefetch_rule(context: models.Context):
  # Make sure that we have the IAM policy in cache.
  iam.get_project_policy(context)


def prepare_rule(context: models.Context):
  logs_by_project[context.project_id] = logs.query(
      project_id=context.project_id,
      resource_type='dataflow_step',
      log_name='log_id("cloudaudit.googleapis.com/activity")',
      filter_str=' AND '.join(LOG_FILTER),
  )


def run_rule(context: models.Context, report: lint.LintReportRuleInterface):
  has_role = True

  project = crm.get_project(context.project_id)
  policies_by_project[context.project_id] = iam.get_project_policy(context)

  # skip entire rule if logging is disabled
  if not apis.is_enabled(context.project_id, 'logging'):
    report.add_skipped(project, 'logging api is disabled')
    return

  # skip entire rule if dataflow API is disabled
  if not apis.is_enabled(context.project_id, 'dataflow'):
    report.add_skipped(project, 'dataflow api is disabled')
    return

  if context.project_id in logs_by_project:
    failed_jobs = set()
    for log_entry in logs_by_project[context.project_id].entries:
      service_account = get_path(
          log_entry,
          ('protoPayload', 'request', 'serviceAccount'),
      )

      job_id = get_path(
          log_entry,
          ('protoPayload', 'request', 'job_id'),
      )

      sa_dataflow_worker_role = policies_by_project[
          context.project_id].has_role_permissions(
              member=f'serviceAccount:{service_account}', role=WORKER_ROLE)

      sa_owner_role = policies_by_project[
          context.project_id].has_role_permissions(
              member=f'serviceAccount:{service_account}', role=OWNER_ROLE)

      sa_editor_role = policies_by_project[
          context.project_id].has_role_permissions(
              member=f'serviceAccount:{service_account}', role=EDITOR_ROLE)

      if sa_dataflow_worker_role or sa_owner_role or sa_editor_role:
        continue
      else:
        has_role = False
        failed_jobs.add('SA ' + service_account + ' used in ' + job_id + ' ' +
                        'does not has the role roles/dataflow.worker \n')

    if failed_jobs:
      report.add_failed(
          project,
          'Some Dataflow jobs in which worker SA did not have Dataflow Worker'
          ' role: ' + ', '.join(itertools.islice(failed_jobs, 100)),
      )

  if has_role:
    report.add_ok(project)
