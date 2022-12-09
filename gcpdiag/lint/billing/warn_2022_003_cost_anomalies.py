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
from gcpdiag.queries import billing, crm

cost_insights = {}


def prepare_rule(context: models.Context):
  cost_insights['insight'] = billing.get_cost_insights_for_a_project(
      context.project_id)


def run_rule(context: models.Context, report: lint.LintReportRuleInterface):
  project = crm.get_project(context.project_id)
  cost_insight = cost_insights['insight']
  if cost_insight.is_anomaly():
    report.add_failed(project, 'Cost Anomaly Found',
                      cost_insight.build_anomaly_description())
  else:
    # no cost anomalies found
    report.add_ok(project, 'No cost anomalies found.')
