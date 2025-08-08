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
"""Common steps for Pub/Sub runbooks."""

from gcpdiag import runbook
from gcpdiag.queries import crm, monitoring, quotas
from gcpdiag.runbook import op
from gcpdiag.runbook.pubsub import flags


class PubsubQuotas(runbook.Step):
  """Has common step to check if any Pub/Sub quotas are being exceeded in the project."""

  template = 'generics::quota_exceeded'

  def execute(self):
    """Checks if any Pub/Sub quotas are being exceeded."""
    if self.quota_exceeded_found is True:
      op.add_failed(
          resource=crm.get_project(op.get(flags.PROJECT_ID)),
          reason=op.prep_msg(op.FAILURE_REASON),
          remediation=op.prep_msg(op.FAILURE_REMEDIATION),
      )
    else:
      op.add_ok(
          resource=crm.get_project(op.get(flags.PROJECT_ID)),
          reason='Quota usage is within project limits.',
      )

  def quota_exceeded_found(self) -> bool:
    quota_exceeded_query = (
        quotas.QUOTA_EXCEEDED_HOURLY_PER_SERVICE_QUERY_TEMPLATE.format(
            service_name='pubsub', within_days=1))
    time_series = monitoring.query(op.get(flags.PROJECT_ID),
                                   quota_exceeded_query)
    if time_series:
      return True
    return False
