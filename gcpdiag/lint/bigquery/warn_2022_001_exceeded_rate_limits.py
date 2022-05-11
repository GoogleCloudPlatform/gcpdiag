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
"""BigQuery is not exceeding rate limits

BigQuery has various quotas that limit the rate and volume of incoming
requests. These quotas exist both to protect the backend systems, and to help
guard against unexpected billing if you submit large jobs.
"""
from gcpdiag import lint, models
from gcpdiag.queries import apis, crm, logs

RATE_LIMITS_FILTER = [
    'severity=ERROR',
    'protoPayload.@type="type.googleapis.com/google.cloud.audit.AuditLog"',
    'protoPayload.serviceData.jobCompletedEvent.job.jobStatus.'
    'additionalErrors.message=~"Exceeded rate limits.*"'
]

logs_by_project = {}


def prepare_rule(context: models.Context):
  logs_by_project[context.project_id] = logs.query(
      project_id=context.project_id,
      resource_type='bigquery_resource',
      log_name='log_id("cloudaudit.googleapis.com/data_access")',
      filter_str=' AND '.join(RATE_LIMITS_FILTER))


def run_rule(context: models.Context, report: lint.LintReportRuleInterface):
  project = crm.get_project(context.project_id)

  # skip entire rule is logging disabled
  if not apis.is_enabled(context.project_id, 'logging'):
    report.add_skipped(project, 'logging api is disabled')
    return

  if not apis.is_enabled(context.project_id, 'bigquery'):
    report.add_skipped(project, 'bigquery api is disabled')
    return

  if logs_by_project.get(context.project_id) and \
     logs_by_project[context.project_id].entries:
    report.add_failed(project, 'exceeded BigQuery rate limits')
  else:
    report.add_ok(project)
