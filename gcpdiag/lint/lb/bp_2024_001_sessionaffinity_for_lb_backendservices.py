# Copyright 2022 Google LLC
# Licensed under the Apache License, Version 2.0 (the "License");
# You may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Session affinity is configured on backends for global external application load balancers

Performance best practices recommend that configuring session affinity
might be beneficial in some scenarios.
"""
from gcpdiag import lint, models
from gcpdiag.queries import lb

EXTERNAL_MANAGED = 'EXTERNAL_MANAGED'
MAX_BACKENDSERVICES_TO_REPORT = 10


def run_rule(context: models.Context, report: lint.LintReportRuleInterface):

  bs_list = lb.get_backend_services(context.project_id)

  # return if there are no BackendServices found in the project
  if not bs_list:
    report.add_skipped(None, 'no backend services found')
    return

  for bs in bs_list:
    # fail for backend services for GXLB which don't have session affinity configured
    if (bs.load_balancing_scheme == EXTERNAL_MANAGED and
        bs.session_affinity == 'NONE' and bs.region == 'None'):
      report.add_failed(bs)

    # pass for backend services for GXLB which have session affinity configured
    elif (bs.load_balancing_scheme == EXTERNAL_MANAGED and
          bs.session_affinity != 'NONE' and bs.region == 'None'):
      report.add_ok(bs)
    else:
      # skip for non-global application LB backend services
      report.add_skipped(
          bs, 'Non Global application Load balancer backend service')
