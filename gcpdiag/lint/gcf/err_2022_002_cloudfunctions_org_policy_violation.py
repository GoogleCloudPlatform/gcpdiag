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
"""Successful Cloud Function deployments.

Log entries indicate a Cloud Functions deployment failure at a region due to a
Resource Location restriction not allowing the region.
"""

from boltons.iterutils import get_path

from gcpdiag import lint, models
from gcpdiag.queries import crm, logs

MATCH_STR = 'The request has violated one or more Org Policies. \
Please refer to the respective violations for more information.'

METHOD_NAME = 'google.cloud.functions.v1.CloudFunctionsService.GenerateUploadUrl'

logs_by_project = {}

LOG_FILTER = [
    'severity=ERROR',
    'protoPayload.@type="type.googleapis.com/google.cloud.audit.AuditLog"',
    f'protoPayload.methodName="{METHOD_NAME}"',
    f'protoPayload.status.message:"{MATCH_STR}"'
]


def prepare_rule(context: models.Context):
  logs_by_project[context.project_id] = logs.query(
      project_id=context.project_id,
      resource_type='cloud_function',
      log_name='log_id("cloudaudit.googleapis.com/data_access")',
      filter_str=' AND '.join(LOG_FILTER))


def run_rule(context: models.Context, report: lint.LintReportRuleInterface):
  project_id = context.project_id
  project_resource = crm.get_project(project_id)
  if not project_resource:
    report.add_skipped(None, f'no projects found {context}')
    return
  query = logs_by_project[context.project_id]
  for log_entry in query.entries:
    message = get_path(log_entry, ('protoPayload', 'status', 'message'),
                       default='')
    severity = get_path(log_entry, ('severity'), default='')
    if MATCH_STR not in message or severity != 'ERROR':
      continue
    entry_project_id = get_path(log_entry, ('resource', 'labels', 'project_id'),
                                default='')
    if entry_project_id == project_id:
      deployment_region = log_entry.get('resource').get('labels').get('region')
      report.add_failed(
          project_resource,
          f'{project_id} had a Cloud Function deployment failure at {deployment_region}'
      )
      break
  else:
    report.add_ok(project_resource)
