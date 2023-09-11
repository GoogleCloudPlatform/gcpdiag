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
"""BigQuery subscription should have a dead-letter topic attached.

A BigQuery subscription could be configured to forward undeliverable/failed
messages to a special dead-letter topic for further analysis/handling.
"""

from gcpdiag import lint, models
from gcpdiag.queries import pubsub


def run_rule(context: models.Context, report: lint.LintReportRuleInterface):
  """Check if the BigQuery subscription has dead-letter topic ."""
  subscriptions = pubsub.get_subscriptions(context)
  if not subscriptions:
    report.add_skipped(None, "no subscriptions found")
  for _, subscription in sorted(subscriptions.items()):
    if subscription.is_big_query_subscription():
      if subscription.has_dead_letter_topic():
        report.add_ok(subscription)
      else:
        report.add_failed(subscription, "has no dead-letter topic attached")
    else:
      report.add_skipped(subscription, "is not a BigQuery Subscription")
