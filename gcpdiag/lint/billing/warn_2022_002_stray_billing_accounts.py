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
"""Billing Accounts have at least one project associated with them

Check whether all active billing accounts the user has permission to view have
at least one project associated with them.

"""

from gcpdiag import lint, models
from gcpdiag.queries import apis, billing, crm

all_account_billing_info = []


def prepare_rule(context: models.Context):
  billing_accounts = billing.get_all_billing_accounts(context.project_id)
  if billing_accounts:
    all_account_billing_info.extend(billing_accounts)


def run_rule(context: models.Context, report: lint.LintReportRuleInterface):
  if not apis.is_enabled(context.project_id, 'cloudbilling'):
    # an API error is raised
    billing.get_billing_info(context.project_id)
    return
  if len(all_account_billing_info) == 0:
    report.add_skipped(None, 'Billing Account Permission Denied')
    return
  project = crm.get_project(context.project_id)
  for billing_account in all_account_billing_info:
    if not len(billing_account.list_projects(context)) > 0:
      report.add_failed(billing_account, 'billing account does not have any '
                        'projects')
      return
  # all billing account have projects associated with them
  report.add_ok(project, 'Billing account has projects linked correctly.')
