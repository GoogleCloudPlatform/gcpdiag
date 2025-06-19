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
"""Contains generalized Cloud logging related Steps """
import re
from typing import Optional

from gcpdiag import runbook, utils
from gcpdiag.queries import crm, logs
from gcpdiag.runbook import op
from gcpdiag.runbook.gcp import flags


class CheckIssueLogEntry(runbook.Step):
  """Checks logs for problematic entry using filter string provided.

  Attributes:
    project_id(str): Project ID to search for filter
    filter_str(str): Filter written in log querying language:
      https://cloud.google.com/logging/docs/view/query-library.
      This field required because an empty filter matches all log entries.
    template(str): Custom template for logging issues related to a resource
      type
    resource_name (Optional[str]): Resource identifier that will be used in
      the custom template provided.
  """

  project_id: str
  filter_str: str
  template: str = 'logging::default'
  issue_pattern: Optional[list[str]] = []
  resource_name: Optional[str] = None

  def execute(self):
    """Check for log entries matching problematic filter string"""

    project = crm.get_project(self.project_id)

    try:
      fetched_logs = logs.realtime_query(project_id=self.project_id,
                                         filter_str=self.filter_str,
                                         start_time=op.get(flags.START_TIME),
                                         end_time=op.get(flags.END_TIME))
    except utils.GcpApiError as err:
      self.template = 'logging::default'
      op.add_skipped(project,
                     reason=op.prep_msg(op.SKIPPED_REASON,
                                        api_err=err,
                                        query=self.filter_str))
    else:
      remediation = None
      reason = None
      self.filter_str += (f'timestamp >= "{op.get(flags.START_TIME)}"'
                          f' AND timestamp <= "{op.get(flags.END_TIME)}"\n')
      if fetched_logs and _pattern_exists_in_entries(self.issue_pattern,
                                                     fetched_logs):
        if self.template != 'logging::default' and self.resource_name:
          reason = op.prep_msg(op.FAILURE_REASON,
                               resource_name=self.resource_name,
                               project_id=self.project_id,
                               query=self.filter_str)
          remediation = op.prep_msg(op.FAILURE_REMEDIATION,
                                    query=self.filter_str,
                                    resource_name=self.resource_name,
                                    project_id=self.project_id)
        else:
          reason = op.prep_msg(op.FAILURE_REASON, query=self.filter_str)
          remediation = op.prep_msg(op.FAILURE_REMEDIATION,
                                    query=self.filter_str)

        op.add_failed(project, reason=reason, remediation=remediation)
      else:
        if self.template != 'logging::default' and self.resource_name:
          reason = op.prep_msg(op.UNCERTAIN_REASON,
                               resource_name=self.resource_name,
                               query=self.filter_str,
                               project_id=self.project_id)
          remediation = op.prep_msg(op.UNCERTAIN_REMEDIATION,
                                    query=self.filter_str,
                                    resource_name=self.resource_name,
                                    project_id=self.project_id)
        else:
          reason = op.prep_msg(op.UNCERTAIN_REASON, query=self.filter_str)
          remediation = op.prep_msg(op.UNCERTAIN_REMEDIATION,
                                    query=self.filter_str)
        op.add_uncertain(project, reason=reason, remediation=remediation)


def _pattern_exists_in_entries(issue_pattern, fetched_logs):
  for log_entry in fetched_logs:
    message = log_entry.get('protoPayload', {}).get('status', {}).get('message')
    if message:
      for pattern_str in issue_pattern:
        if re.search(pattern_str, message):
          return True
  return False
