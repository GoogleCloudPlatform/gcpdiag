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
"""Health check logging is enabled on health checks for load balancer backend services

Best practice recommends that health check logging is enabled on health checks
for load balancer backend services.
"""

from gcpdiag import lint, models
from gcpdiag.queries import gce, lb

bs_health_checks = set()
bs_list = {}


def prefetch_rule(context: models.Context):
  bs_list[context.project_id] = lb.get_backend_services(context.project_id)
  if not bs_list[context.project_id]:
    return
  # prefetch health checks
  for bs in bs_list[context.project_id]:
    if bs.health_check:
      health_check = gce.get_health_check(context.project_id, bs.health_check)
      del health_check


def run_rule(context: models.Context, report: lint.LintReportRuleInterface):
  # return if there are no BackendServices found in the project
  backend_services = bs_list[context.project_id]
  if not backend_services:
    report.add_skipped(None, 'no backend services found')
    return
  # get the health check resouce object for each backend service
  for bs in backend_services:
    if bs.health_check:
      health_check = gce.get_health_check(context.project_id, bs.health_check)
      bs_health_checks.add(health_check)
    else:
      report.add_skipped(bs, 'No health check configured on backend service')
  # check that logging is enabled on the health check.
  for health_check in bs_health_checks:
    if health_check.is_log_enabled:
      report.add_ok(health_check)
    else:
      report.add_failed(health_check)
