# Copyright 2024 Google LLC
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
"""Having the composer API enabled ensures the environment remains in a healthy state.

Disabling the Cloud Composer's service (API) puts Composer environments into a
permanent failed state, and permanently deletes the Composer tenant project.
Make sure that all Cloud Composer environments in your project are deleted.
"""

from boltons.iterutils import get_path

from gcpdiag import lint, models
from gcpdiag.queries import apis, composer, crm, logs

MATCH_STR1 = 'google.api.serviceusage.v1.ServiceUsage.DisableService'
MATCH_STR2 = 'google.api.serviceusage.v1.ServiceUsage.EnableService'
MATCH_STR3 = '/services/composer.googleapis.com'

FILTER_1 = [
    f'protoPayload.methodName = ("{MATCH_STR1}" OR "{MATCH_STR2}")',
    f'protoPayload.request.name=~ ("{MATCH_STR3}")',
]

logs_by_project = {}
envs_by_project = {}


def prefetch_rule(context: models.Context):
  envs_by_project[context.project_id] = composer.get_environments(context)


def prepare_rule(context: models.Context):
  logs_by_project[context.project_id] = logs.query(
      project_id=context.project_id,
      resource_type='audited_resource',
      log_name='log_id("cloudaudit.googleapis.com/activity")',
      filter_str=' AND '.join(FILTER_1),
  )


def run_rule(context: models.Context, report: lint.LintReportRuleInterface):
  """Run the rule."""
  project = crm.get_project(context.project_id)

  if not apis.is_enabled(context.project_id, 'logging'):
    report.add_skipped(None, 'logging api is disabled')
    return

  if (logs_by_project.get(context.project_id) and
      logs_by_project[context.project_id].entries):
    for log_entry in logs_by_project[context.project_id].entries:
      # Filter out non-relevant log entries.
      if MATCH_STR1 in get_path(log_entry, ('protoPayload', 'methodName'),
                                '') and MATCH_STR3 in get_path(
                                    log_entry,
                                    ('protoPayload', 'request', 'name'), ''):
        report.add_failed(project,
                          'Request to disable the composer API recently done')
        return

      if MATCH_STR2 in get_path(log_entry, ('protoPayload', 'methodName'),
                                '') and MATCH_STR3 in get_path(
                                    log_entry,
                                    ('protoPayload', 'request', 'name'), ''):

        envs = envs_by_project[context.project_id]

        if envs:
          report.add_failed(
              project,
              'Re-enabling the composer API (after disabling),You may see the '
              ' the active environment entered into an error state.',
          )
          return

  # in case of there is no log or all logs are non-relevant
  report.add_ok(project)
