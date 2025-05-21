# Copyright 2022 Google LLC
# Licensed under the Apache License, Version 2.0 (the "License");
# You may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Backend Service Timeout for Global External Application Load Balancers.

The default timeout is 30 seconds for external application load balancers
and we don't recommend backend service timeout values greater than 24 hours
(86,400 seconds) because Google Cloud periodically restarts GFEs for software
updates and other routine maintenance. The longer the backend service timeout
value, the more likely it is that Google Cloud terminates TCP connections for
maintenance.
"""

from gcpdiag import lint, models
from gcpdiag.queries import lb

MAX_BACKENDSERVICES_TO_REPORT = 10


def run_rule(context: models.Context, report: lint.LintReportRuleInterface):

  bs_list = lb.get_backend_services(context.project_id)

  # return if there are no BackendServices found in the project
  if not bs_list:
    report.add_skipped(None, 'no backend services found')
    return

  for bs in bs_list:
    # fail for backend services where backend service timeout is greater than 24
    # hours for external application load balancers
    if (bs.load_balancing_scheme in ('EXTERNAL_MANAGED', 'EXTERNAL') and
        bs.timeout_sec > 86400):
      report.add_failed(bs)

    # pass for backend services with timeout less than 24 hours.
    elif (bs.load_balancing_scheme in ('EXTERNAL_MANAGED', 'EXTERNAL') and
          bs.timeout_sec < 86400):
      report.add_ok(bs)

    else:
      # skip for others
      report.add_skipped(bs, 'No external load balancer backend services found')
