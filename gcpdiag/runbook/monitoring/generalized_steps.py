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
from gcpdiag.runbook import op
from gcpdiag.runbook.gcp import flags


class TimeSeriesCheck(runbook.Step):
  """Assess if a given metric is has expected values..

  Currently checks if an attribute
  - Currently checks if metrics exists indicating a problem
  - Improve to be more flexible.
  """
  template = 'metrics::default'
  query: str
  query_kwargs: dict
  resource: Resource

  def execute(self):
    """Verify if expected metrics value is present or not"""
    metrics = None
    metrics = monitoring.query(op.get(flags.PROJECT_ID),
                               self.query.format(self.query_kwargs))

    if metrics:
      op.add_failed(self.resource,
                    reason=op.prep_msg(op.FAILURE_REASON),
                    remediation=op.prep_msg(op.FAILURE_REMEDIATION))
    else:
      op.add_ok(self.resource, reason=op.prep_msg(op.SUCCESS_REASON))
