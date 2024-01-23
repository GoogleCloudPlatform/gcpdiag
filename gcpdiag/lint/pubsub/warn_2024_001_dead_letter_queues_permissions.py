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

# Lint as: python3
"""Pub/Sub service account has the Publisher and Subscriber Permissions if DLQ exist.

To forward undeliverable messages to a dead-letter topic, Pub/Sub must have the
'roles/pubsub.subscriber' and 'roles/pubsub.publisher' permissions enabled on the
automatically created Pub/Sub service account.
"""

import re

from gcpdiag import lint, models
from gcpdiag.queries import crm, iam, pubsub

role_publisher = 'roles/pubsub.publisher'
role_subscriber = 'roles/pubsub.subscriber'

policy_by_project = {}
projects = {}


def prefetch_rule(context: models.Context):
  projects[context.project_id] = crm.get_project(context.project_id)
  policy_by_project[context.project_id] = iam.get_project_policy(
      context.project_id)


def run_rule(context: models.Context, report: lint.LintReportRuleInterface):
  """Check if the subscription has dead-letter topic ."""

  subscriptions = pubsub.get_subscriptions(context)

  if not subscriptions:
    report.add_skipped(None, 'no subscriptions found')
    return

  project = projects[context.project_id]

  dlq_subscriptions_exist = False
  required_permission = True

  for _, subscription in subscriptions.items():
    if subscription.has_dead_letter_topic():
      dlq_subscriptions_exist = True
      break

  if not dlq_subscriptions_exist:
    report.add_skipped(None, 'has no dead-letter topic attached')
    return

  else:
    project_policy = policy_by_project[context.project_id]
    service_account_re = re.compile('serviceAccount:service-' +
                                    str(project.number) +
                                    '@gcp-sa-pubsub.iam.gserviceaccount.com')
    service_account = next(
        filter(
            service_account_re.match,
            project_policy.get_members(),
        ),
        None,
    )

    if not service_account:
      report.add_failed(project, 'no Pub/Sub Service Account found')

    if not project_policy.has_role_permissions(service_account, role_publisher):
      report.add_failed(
          project,
          f'{service_account}\nmissing role: {role_publisher}',
      )
      required_permission = False

    if not project_policy.has_role_permissions(service_account,
                                               role_subscriber):
      report.add_failed(
          project,
          f'{service_account}\nmissing role: {role_subscriber}',
      )
      required_permission = False

  if dlq_subscriptions_exist and required_permission:
    report.add_ok(project)
