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
the messages will be discarded from Pub/Sub regardless, resulting in loss of
data published to the topic.
"""

from gcpdiag import lint, models
from gcpdiag.queries import crm, pubsub


def run_rule(context: models.Context, report: lint.LintReportRuleInterface):
  """Check if a valid topic has a subscription attached."""
  topics = pubsub.get_topics(context)
  subscriptions = pubsub.get_subscriptions(context)

  for _, subscription in subscriptions.items():
    if (subscription.topic != "_deleted_topic_" and
        subscription.topic.full_path in topics):
      del topics[subscription.topic.full_path]

  if topics:
    for _, topic in topics.items():
      report.add_failed(topic)
  else:
    report.add_ok(
        crm.get_project(context.project_id),
        "All active topics have subscriptions",
    )
