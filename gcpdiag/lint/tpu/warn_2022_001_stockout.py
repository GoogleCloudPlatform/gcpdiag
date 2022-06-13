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
"""Cloud TPU resource availability

Resource errors occur when you try to request new resources in a zone that
cannot accommodate your request due to the current unavailability of a Cloud
TPU resource.
"""
from boltons.iterutils import get_path

from gcpdiag import lint, models
from gcpdiag.queries import apis, crm, logs

MATCH_STR = 'There is no more capacity in the zone'
MATCH_STR2 = 'you can try in another zone where Cloud TPU Nodes'
METHOD_NAME = 'google.cloud.tpu.v1.Tpu.CreateNode'

LOG_FILTER = [
    'severity=ERROR',
    f'protoPayload.methodName="{METHOD_NAME}"',
    f'protoPayload.status.message:"{MATCH_STR}"',
    f'protoPayload.status.message:"{MATCH_STR2}"',
]

logs_by_project = {}


def prepare_rule(context: models.Context):
  logs_by_project[context.project_id] = logs.query(
      project_id=context.project_id,
      resource_type='audited_resource',
      log_name='log_id("cloudaudit.googleapis.com/activity")',
      filter_str=' AND '.join(LOG_FILTER))


def run_rule(context: models.Context, report: lint.LintReportRuleInterface):
  project = crm.get_project(context.project_id)

  if not apis.is_enabled(context.project_id, 'tpu'):
    report.add_skipped(project, 'tpu api is disabled')
    return

  # skip entire rule is logging disabled
  if not apis.is_enabled(context.project_id, 'logging'):
    report.add_skipped(project, 'logging api is disabled')
    return

  if logs_by_project.get(context.project_id) and \
     logs_by_project[context.project_id].entries:
    for log_entry in logs_by_project[context.project_id].entries:
      # Filter out non-relevant log entries.
      if log_entry['severity'] != 'ERROR' or \
         METHOD_NAME not in get_path(log_entry,
                     ('protoPayload', 'methodName'), default='') or \
         MATCH_STR not in get_path(log_entry,
                     ('protoPayload', 'status', 'message'), default='') or \
         MATCH_STR2 not in get_path(log_entry,
                     ('protoPayload', 'status', 'message'), default=''):
        continue
      report.add_failed(project,
                        'TPU failed to create due to resource availability')
      return

  # in case of there is no log or all logs are non-relevant
  report.add_ok(project)
