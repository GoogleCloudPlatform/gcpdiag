# Copyright 2023 Google LLC
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
"""Cloud Composer private IP Cluster non-RFC1918 IP range.

Private IP cluster (Pods, Services) Should use ALLOWED IP RANGES
to create the environment.Make sure you are using ALLOWED IP RANGES
during environment Creation.
"""

import re

from gcpdiag import lint, models
from gcpdiag.queries import apis, crm, logs

logs_by_project = {}

MATCH_STR1 = (
    'type.googleapis.com/google.cloud.orchestration.airflow.service.v1.CreateEnvironmentRequest'
)
MATCH_STR2 = (
    'type.googleapis.com/google.cloud.orchestration.'\
    'airflow.service.v1beta1.CreateEnvironmentRequest'
)
pattern = (
    r'(Cluster|Services|GKE master) CIDR range (\d+\.\d+\.\d+\.\d+/\d+) is not'
    r' within allowed ranges.')
ip_pattern = r'(\d+\.\d+\.\d+\.\d+/\d+)'

FILTER_1 = [f'protoPayload.request.@type={MATCH_STR1} OR {MATCH_STR2}']


def prepare_rule(context: models.Context):
  logs_by_project[context.project_id] = logs.query(
      project_id=context.project_id,
      resource_type='cloud_composer_environment',
      log_name='log_id("cloudaudit.googleapis.com%2Factivity")',
      filter_str=' AND '.join(FILTER_1),
  )


def run_rule(context: models.Context, report: lint.LintReportRuleInterface):

  project = crm.get_project(context.project_id)

  if not apis.is_enabled(context.project_id, 'composer'):
    report.add_skipped(None, 'composer is disabled')
    return

  if not apis.is_enabled(context.project_id, 'logging'):
    report.add_skipped(None, 'logging api is disabled')
    return

  # Log entries
  log_entries = logs_by_project.get(context.project_id)

  if not log_entries:
    report.add_skipped(None, 'No log entries found')
    return

  project_ok_flag = True

  # Start Iteration from the latest log entries
  for log_entry in reversed(log_entries.entries):
    # Check for the not allowed IP Range Error Entry
    if (log_entry['severity'] == 'ERROR' and
        log_entry['protoPayload']['status']['code'] == 3):
      message_body = log_entry['protoPayload']['status']['message']
      match = re.search(pattern, message_body)
      if not match:
        continue
      else:
        matches = re.findall(ip_pattern, message_body)
        ip_ranges = set(matches)
        report.add_failed(
            project,
            f'{ip_ranges} outsides the ALLOWED IP RANGE \n'
            'Try Creating private IP cluster using ALLOWED IP RANGES',
        )
      project_ok_flag = False
      break

    # Check for the latest successful environment creation
    if log_entry['severity'] == 'NOTICE':
      report.add_ok(project)
      return

  if project_ok_flag:
    report.add_ok(project)
