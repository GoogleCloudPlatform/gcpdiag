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

from boltons.iterutils import get_path

from gcpdiag import runbook
from gcpdiag.models import Resource
from gcpdiag.queries import logs
from gcpdiag.runbook import op
from gcpdiag.runbook.gcp import flags


class LogsCheck(runbook.Step):
  """Assess if a given log query is present or not..

  Checks if a log attribute has a bad or good pattern
  """
  template = 'logging::default'
  log_name: str
  resource_type: str
  filter_str: str
  attribute: tuple
  good_pattern: str
  bad_pattern: str
  resource: Resource

  def execute(self):
    """Inspecting cloud logging for good or bad patterns"""
    fetched_logs = logs.realtime_query(project_id=op.get(flags.PROJECT_ID),
                                       filter_str=self.filter_str,
                                       start_time_utc=op.get(
                                           flags.START_TIME_UTC),
                                       end_time_utc=op.get(flags.END_TIME_UTC))
    for entry in fetched_logs:
      actual_value = get_path(entry, self.attribute, None)

      if re.match(self.bad_pattern, actual_value, re.IGNORECASE):
        self.interface.add_failed(self.resource,
                                  reason=op.prep_msg(op.FAILURE_REASON),
                                  remediation=op.prep_msg(
                                      op.FAILURE_REMEDIATION))
      elif re.match(self.good_pattern, actual_value, re.IGNORECASE):
        self.interface.add_ok(self.resource,
                              reason=op.prep_msg(op.SUCCESS_REASON))
