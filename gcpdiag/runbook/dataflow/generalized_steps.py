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
"""Common steps for Dataflow runbooks."""

from gcpdiag import runbook
from gcpdiag.queries import dataflow
from gcpdiag.runbook import op
from gcpdiag.runbook.dataflow import flags


class ValidSdk(runbook.Step):
  """Has common step to check if the job is running a valid SDK.

  Contains SDK check Step that are likely to be reused for most Dataflow
  Runbooks.
  """

  def execute(self):
    """Checks SDK is not in the list that might trigger known SDK issues."""
    job = dataflow.get_job(
        op.get(flags.PROJECT_ID),
        op.get(flags.DATAFLOW_JOB_ID),
        op.get(flags.JOB_REGION),
    )
    if job.sdk_support_status != 'SUPPORTED':
      op.add_failed(
          resource=None,
          reason=('Dataflow job Beam SDK is not supported. The pipeline may be'
                  ' rejected.'),
          remediation='Please use a supported Beam SDK version',
      )
    else:
      op.add_ok(resource=job, reason='Dataflow job Beam SDK is supported.')
