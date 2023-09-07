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
"""Each topic has at least one subscription attached.

Without a subscription, subscribers cannot pull messages or receive pushed
messages published to the topic. At the end of the max message retention period,
the messages will be discarded from Pub/Sub regardless.
"""

from gcpdiag import lint, models
from gcpdiag.queries import pubsub


def run_rule(context: models.Context, report: lint.LintReportRuleInterface):
  """Check if topic has a subscription attached."""
  topics = pubsub.get_topics(context)
  subscriptions = pubsub.get_subscription(context)

  subscription_topics = set()
  for _, subscription in subscriptions.items():
    subscription_topics.add(subscription.topic.name)

  for _, topic in topics.items():
    if topic.name not in subscription_topics:
      report.add_failed(topic, "has no subscription attached")
    else:
      report.add_ok(topic)
