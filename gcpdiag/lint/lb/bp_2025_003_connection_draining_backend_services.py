# Copyright 2025 Google LLC
# Licensed under the Apache License, Version 2.0 (the "License");
# You may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Connection draining timeout is configured for proxy load balancers.

Performance best practices recommend configuring connection draining
timeout to allow existing requests to complete when instances are removed
from a backend service.
"""
from gcpdiag import lint, models
from gcpdiag.queries import lb


def run_rule(context: models.Context, report: lint.LintReportRuleInterface):

  bs_list = lb.get_backend_services(context.project_id)

  # return if there are no BackendServices found in the project
  if not bs_list:
    report.add_skipped(None, 'No backend services found in this project.')
    return

  # Define load balancer types for which connection draining is applicable.
  proxy_lb_types = [
      lb.LoadBalancerType.GLOBAL_EXTERNAL_PROXY_NETWORK_LB,
      lb.LoadBalancerType.REGIONAL_INTERNAL_PROXY_NETWORK_LB,
      lb.LoadBalancerType.REGIONAL_EXTERNAL_PROXY_NETWORK_LB,
      lb.LoadBalancerType.CROSS_REGION_INTERNAL_PROXY_NETWORK_LB,
      lb.LoadBalancerType.CLASSIC_PROXY_NETWORK_LB,
      lb.LoadBalancerType.GLOBAL_EXTERNAL_APPLICATION_LB,
      lb.LoadBalancerType.REGIONAL_INTERNAL_APPLICATION_LB,
      lb.LoadBalancerType.REGIONAL_EXTERNAL_APPLICATION_LB,
      lb.LoadBalancerType.CROSS_REGION_INTERNAL_APPLICATION_LB,
      lb.LoadBalancerType.CLASSIC_APPLICATION_LB,
  ]

  for bs in bs_list:
    if bs.load_balancer_type in proxy_lb_types:
      if bs.draining_timeout_sec > 0:
        report.add_ok(
            bs,
            'Connection draining timeout is configured:'
            f' {bs.draining_timeout_sec} seconds.',
        )
      else:
        report.add_failed(
            bs,
            'Connection draining timeout is not configured (set to 0 seconds).',
        )
    else:
      report.add_skipped(
          bs,
          'Connection draining timeout not applicable to this load balancer'
          ' type.',
      )
