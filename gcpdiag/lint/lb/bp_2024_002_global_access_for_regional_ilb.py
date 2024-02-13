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
"""Global Access enabled on Regional Internal Load Balancer.

When global access is not on, resources in other location might not be able to
visit the Internal Load Balancer(iLB). It's recommended to enable the global
access in regional iLB.
"""

from gcpdiag import lint, models
from gcpdiag.queries import lb

forwarding_rules_list = {}


def prefetch_rule(context: models.Context):
  forwarding_rules_list[context.project_id] = lb.get_forwarding_rules(
      context.project_id)


def run_rule(context: models.Context, report: lint.LintReportRuleInterface):

  forwarding_rules = forwarding_rules_list[context.project_id]
  # return if there is no forwarding_rule found in the project
  if not forwarding_rules:
    report.add_skipped(None, 'no Forwarding Rules found')
    return

  for forwarding_rule in forwarding_rules:
    if not forwarding_rule.is_global_access_allowed:
      report.add_failed(forwarding_rule)
    else:
      report.add_ok(forwarding_rule)
