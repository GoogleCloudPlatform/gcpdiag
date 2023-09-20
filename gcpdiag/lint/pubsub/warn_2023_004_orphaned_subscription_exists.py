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
"""Project should not have a subscription without a topic attached.

For a subscription whose topic is deleted, it cannot be reattached to a new
topic and thus cannot receive new published messages. Messages in the
subscription will expire after the message retention period if unacked,
and discarded from Pub/Sub which may lead to data loss.
The subscription is then counting as quota consumed for an unusable resource.
"""

from gcpdiag import lint, models
from gcpdiag.queries import crm, pubsub


def run_rule(context: models.Context, report: lint.LintReportRuleInterface):
  """Check if subscription is attached to a valid topic."""
  subscriptions = pubsub.get_subscriptions(context)
  orphaned_subscription_exists = False
  if not subscriptions:
    report.add_skipped(None, "no subscriptions found")

  for _, subscription in subscriptions.items():
    if subscription.topic == "_deleted_topic_":
      report.add_failed(subscription)
      orphaned_subscription_exists = True

  if not orphaned_subscription_exists:
    report.add_ok(crm.get_project(context.project_id))
