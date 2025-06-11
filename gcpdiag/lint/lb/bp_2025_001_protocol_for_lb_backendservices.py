# Copyright 2022 Google LLC
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
"""HTTP/2 between load balancer and backend may increase TCP connections.

Connection pooling is not available with HTTP/2 which can lead to high backend
latencies, so wisely select backend protocol
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
    # fail for backend services which have HTTP/2 as backend service protocol
    if bs.protocol == 'HTTP2':
      report.add_failed(bs)

    # pass for backend services which have HTTP(S) as backend service protocol
    else:
      report.add_ok(bs)
