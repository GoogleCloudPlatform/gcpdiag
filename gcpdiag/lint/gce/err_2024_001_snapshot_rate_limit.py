# Copyright 2024 Google LLC
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
"""Snapshot creation not failed due to rate limit.

When you try to snapshot your disk more than once during a ten minute period, or
issue more than six burst snapshot requests in 60 minutes, you will encounter
rate exceeded error. Follow best practices for disk snapshots.
"""

from boltons.iterutils import get_path

from gcpdiag import lint, models
from gcpdiag.queries import apis, crm, logs

ERROR_MSG = 'RESOURCE_OPERATION_RATE_EXCEEDED'
METHOD_NAME_MATCH = 'v1.compute.snapshots.insert'
LOG_FILTER = f"""
severity=ERROR
protoPayload.status.message="{ERROR_MSG}"
protoPayload.methodName="{METHOD_NAME_MATCH}"
"""

logs_by_project = {}


def prepare_rule(context: models.Context):
  logs_by_project[context.project_id] = logs.query(
      project_id=context.project_id,
      resource_type='gce_snapshot',
      log_name='log_id("cloudaudit.googleapis.com/activity")',
      filter_str=LOG_FILTER,
  )


def run_rule(context: models.Context, report: lint.LintReportRuleInterface):
  project = crm.get_project(context.project_id)
  # skip entire rule if gce api is disabled
  if not apis.is_enabled(context.project_id, 'compute'):
    report.add_skipped(project, 'compute api is disabled')
    return

  # skip entire rule if logging disabled
  if not apis.is_enabled(context.project_id, 'logging'):
    report.add_skipped(project, 'logging api is disabled')
    return

  project_ok_flag = True

  if (logs_by_project.get(context.project_id) and
      logs_by_project[context.project_id].entries):
    #Start the Iteration of Log entries
    for entry in logs_by_project[context.project_id].entries:
      msg = get_path(entry, ('protoPayload', 'status', 'message'), default='')
      method = get_path(entry, ('protoPayload', 'methodName'), default='')
      # find the relevant entries
      if (entry['severity'] == 'ERROR' and METHOD_NAME_MATCH in method and
          ERROR_MSG in msg):
        report.add_failed(project, 'Snapshot Creation limit exceeded')
        project_ok_flag = False

  if project_ok_flag:
    report.add_ok(project)
