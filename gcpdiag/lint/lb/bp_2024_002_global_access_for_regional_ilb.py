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
"""Global Access enabled on forwarding rule for Regional Internal Load Balancer.

When global access is not on, resources/clients in other location might not be
able to visit the Internal Load Balancer(iLB). It's recommended to enable the
global access in regional iLB.
"""

import re

from gcpdiag import lint, models
from gcpdiag.queries import lb

INTERNAL = 'INTERNAL'
INTERNAL_MANAGED = 'INTERNAL_MANAGED'

forwarding_rules_list = {}


def prefetch_rule(context: models.Context):
  forwarding_rules_list[context.project_id] = lb.get_forwarding_rules(
      context.project_id)


def run_rule(context: models.Context, report: lint.LintReportRuleInterface):
  """Checks if global access is enabled on regional forwarding rule."""

  forwarding_rules = forwarding_rules_list[context.project_id]
  # return if there is no forwarding_rule found in the project
  if not forwarding_rules:
    report.add_skipped(None, 'no Forwarding Rules found')
    return

  for forwarding_rule in forwarding_rules:
    forwarding_rule_regional = re.match(
        r'projects/([^/]+)/regions/([^/]+)/forwardingRules/([^/]+)',
        forwarding_rule.full_path,
    )
    if forwarding_rule_regional and forwarding_rule.load_balancing_scheme in [
        INTERNAL,
        INTERNAL_MANAGED,
    ]:
      if not forwarding_rule.global_access_allowed:
        report.add_failed(forwarding_rule)
      else:
        report.add_ok(forwarding_rule)
