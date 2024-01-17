# Copyright 2021 Google LLC
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
""" No Unused Service Accounts Found

Unused service accounts create an unnecessary security risk,
so we recommend disabling unused service accounts then deleting the service
accounts when you are sure that you no longer need them
"""

from boltons.iterutils import get_path

from gcpdiag import lint, models
from gcpdiag.queries import iam, monitoring

service_accounts = {}
query_results_per_project_id: dict[str, monitoring.TimeSeriesCollection] = {}
unique_id_set = set()


def prefetch_rule(context: models.Context):
  iam.get_service_account_list(context.project_id)
  query_results_per_project_id[context.project_id] = monitoring.query(
      context.project_id,
      """
      fetch iam_service_account
      | metric 'iam.googleapis.com/service_account/authn_events_count'
      | within 12w
      """,
  )


def run_rule(context: models.Context, report: lint.LintReportRuleInterface):
  service_accounts[context.project_id] = iam.get_service_account_list(
      context.project_id)
  accounts = service_accounts[context.project_id]
  if len(accounts) == 0:
    report.add_skipped(None, 'No Service accounts found')
    return

  for que in query_results_per_project_id[context.project_id].values():
    try:
      val = get_path(que, ('labels', 'resource.unique_id'))
      unique_id_set.add(val)
    except KeyError:
      continue

  for account in accounts:
    if account.unique_id not in unique_id_set:
      report.add_failed(account, 'Unused Service Account Found')
    else:
      report.add_ok(account)
