#
# Copyright 2021 Google LLC
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

# Lint as: python3
"""Check for any billing anomalies using cost insights
"""

from gcpdiag import lint, models
from gcpdiag.queries import apis, billing, crm

cost_insights = {}


def prepare_rule(context: models.Context):
  billing_account = billing.get_billing_account(context.project_id)
  if billing_account:
    cost_insights['insights'] = billing.get_cost_insights_for_a_project(
        context.project_id)


def run_rule(context: models.Context, report: lint.LintReportRuleInterface):
  if not apis.is_enabled(context.project_id, 'cloudbilling'):
    # an API error is raised
    billing.get_billing_info(context.project_id)
    return
  if not cost_insights:
    report.add_skipped(
        None, 'Billing Account Permission Denied or Project Billing Disabled')
    return
  project = crm.get_project(context.project_id)
  cost_insight = cost_insights['insights']
  anomaly_found = False
  for cost_insight in cost_insights['insights']:
    if cost_insight.is_anomaly():
      report.add_failed(project, 'Cost Anomaly Found',
                        cost_insight.build_anomaly_description())
      anomaly_found = True
  if not anomaly_found:
    # no cost anomalies found
    report.add_ok(project, 'No cost anomalies found.')
