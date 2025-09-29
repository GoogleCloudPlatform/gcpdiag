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

# Lint as: python3
"""Pub/Sub service account has BigQuery Permissions if BigQuery Subscription(s) exist.

For any BigQuery subscriptions to deliver messages successfully, they should
have the appropriate BigQuery Editor permissions to the appropriate service.
"""

import re

from gcpdiag import lint, models
from gcpdiag.queries import crm, iam, pubsub

policies = {}


def prefetch_rule(context: models.Context):
  policies[context.project_id] = iam.get_project_policy(context)


def run_rule(context: models.Context, report: lint.LintReportRuleInterface):
  """Check if subscription has relevant BQ permissions."""

  role_bq_data_editor = 'roles/bigquery.dataEditor'
  project = crm.get_project(context.project_id)
  project_nr = crm.get_project(context.project_id).number

  bq_subscriptions_exist = False

  subscriptions = pubsub.get_subscriptions(context)
  if not subscriptions:
    report.add_skipped(None, 'no subscriptions found')

  for _, subscription in subscriptions.items():
    if bq_subscriptions_exist:
      break
    elif subscription.is_big_query_subscription():
      bq_subscriptions_exist = True

  if not bq_subscriptions_exist:
    report.add_skipped(None, 'no BQ subscriptions found')
  else:
    service_account_re = re.compile('serviceAccount:service-' +
                                    str(project_nr) +
                                    '@gcp-sa-pubsub.iam.gserviceaccount.com')
    member = next(
        filter(
            service_account_re.match,
            policies[context.project_id].get_members(),
        ),
        None,
    )

    if not member:
      report.add_failed(project, 'no Pub/Sub Service Account found')
    elif bq_subscriptions_exist and not policies[
        context.project_id].has_role_permissions(member, role_bq_data_editor):
      report.add_failed(
          project,
          f'{member} does not have permissions for the role'
          f' {role_bq_data_editor}',
      )
    else:
      report.add_ok(project)
