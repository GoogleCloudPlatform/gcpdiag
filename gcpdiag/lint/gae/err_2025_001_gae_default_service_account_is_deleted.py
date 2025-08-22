# Copyright 2025 Google LLC
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
"""GAE default service account is deleted

GAE default service account (@appspot.gserviceaccount.com) by default is used
for GAE applications deployment when user-defined service account is not declared

If it's recently deleted, recover the SA otherwise use user-defined service account
"""

from gcpdiag import lint, models
from gcpdiag.queries import apis, crm, logs

delete_sa_logs, failed_deploy_logs = {}, {}


def prepare_rule(context: models.Context):
  log_id = 'log_id("cloudaudit.googleapis.com/activity")'
  status_message = 'The AppEngine default service account might have been manually deleted'
  email = f"{context.project_id}@appspot.gserviceaccount.com"

  failed_deploy_logs[context.project_id] = logs.query(
      project_id=context.project_id,
      log_name=log_id,
      resource_type='gae_app',
      filter_str=
      f'severity="ERROR" AND protoPayload.status.message:"{status_message}"')

  delete_sa_logs[context.project_id] = logs.query(
      project_id=context.project_id,
      log_name=log_id,
      resource_type='service_account',
      filter_str=f'resource.labels.email_id="{email}" \
      AND protoPayload.methodName="google.iam.admin.v1.DeleteServiceAccount"')


def run_rule(context: models.Context, report: lint.LintReportRuleInterface):
  project = crm.get_project(context.project_id)
  # skip entire rule if Logging API is disabled
  if not apis.is_enabled(context.project_id, 'logging'):
    report.add_skipped(project, 'Logging api is disabled')
    return

  # If the customer recently deleted their GAE default SA
  if delete_sa_logs.get(context.project_id) and \
      delete_sa_logs[context.project_id].entries:
    report.add_failed(
        project, 'The App Engine default service account was recently deleted. \
    Please follow the steps at \
    https://cloud.google.com/iam/docs/service-accounts-delete-undelete#undeleting \
    to recover it.')

  # If the customer tried to deploy and failed due to the default service account
  if failed_deploy_logs.get(context.project_id) and \
    failed_deploy_logs[context.project_id].entries:
    report.add_failed(
        project,
        'Failure deploying to App Engine: The App Engine default service account is deleted. \
    Please use a user-managed service account instead.')
  else:
    report.add_ok(project)
