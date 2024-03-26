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
"""Contains generalized steps for Cloud monitoring"""
from gcpdiag import runbook
from gcpdiag.models import Resource
from gcpdiag.queries import monitoring
from gcpdiag.runbook.gcp import constants, flags


class TimeSeriesCheck(runbook.Step):
  """Assess if a given metric is has expected values..

  Currently checks if an attribute
  - Currently checks if metrics exists indicating a problem
  - Improve to be more flexible.
  """
  template = 'metric::default'
  query: str
  query_kwargs: dict
  resource: Resource

  def execute(self):
    """Verifying if expected metrics value is present or not"""
    metrics = None
    metrics = monitoring.query(self.op.get(flags.PROJECT_ID),
                               self.query.format(self.query_kwargs))

    if metrics:
      self.interface.add_failed(
          self.resource,
          reason=self.op.get_msg(constants.FAILURE_REASON),
          remediation=self.op.get_msg(constants.FAILURE_REMEDIATION))
    else:
      self.interface.add_ok(self.resource,
                            reason=self.op.get_msg(constants.SUCCESS_REASON))
