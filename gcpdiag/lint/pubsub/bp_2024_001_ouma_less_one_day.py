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
"""Oldest Unacked Message Age Value less than 24 hours.

Failing to pull messages and ack them within 24 hours could lead to additional
storage charges, as well as potentially overwhelm subscribers who are not
flow-controlled when delivery is begun at a high backlog.
"""

from itertools import islice
from typing import Dict

from boltons.iterutils import get_path

from gcpdiag import lint, models
from gcpdiag.queries import crm, monitoring, pubsub

# ouma == oldest_unacked_message_age
ouma_tracker: Dict[str, monitoring.TimeSeriesCollection] = {}
MAX_SUBSCRIPTIONS_TO_DISPLAY = 10


def prefetch_rule(context: models.Context):
  """Gathers the metric values for the ouma for all subscriptions."""
  subscription_name = ''
  query_ouma = (
      'fetch pubsub_subscription | metric'
      ' "pubsub.googleapis.com/subscription/oldest_unacked_message_age" |'
      ' filter resource.project_id == "{}" &&'
      ' (resource.subscription_id == "{}") | group_by 1m,'
      ' [value_oldest_unacked_message_age_mean:'
      ' mean(value.oldest_unacked_message_age)]| every 1m')

  subscriptions = pubsub.get_subscriptions(context)

  for _, subscription in subscriptions.items():
    subscription_name = subscription.name
    ouma_tracker[subscription_name] = monitoring.query(
        context.project_id,
        query_ouma.format(context.project_id, subscription_name),
    )


def run_rule(context: models.Context, report: lint.LintReportRuleInterface):
  """Checks for ouma value as more than 24 h to get FAIL."""
  project = crm.get_project(context.project_id)

  if not ouma_tracker:
    report.add_skipped(None, 'no subscription metrics found')

  failing_subs = set()
  for subscription_name, ouma_metric in ouma_tracker.items():
    for metric_values in ouma_metric.values():
      # eval needs to unwrap Dict result similar to {..., 'values': [[0.0]]}
      if get_path(metric_values, ('values'))[0][0] > 24:
        failing_subs.add(subscription_name)

  # reporting
  if failing_subs:
    extra_subs = ''
    if len(failing_subs) > MAX_SUBSCRIPTIONS_TO_DISPLAY:
      extra_subs = (', and'
                    f' {len(failing_subs) - MAX_SUBSCRIPTIONS_TO_DISPLAY} more'
                    ' subscriptions')

    # pylint: disable=line-too-long
    report.add_failed(
        project,
        f'{len(failing_subs)} subscriptions have an'
        ' oldest_unacked_message_age of more than 24 hours'
        f" {', '.join(islice(failing_subs, MAX_SUBSCRIPTIONS_TO_DISPLAY))}{extra_subs}",
    )
  # pylint: enable=line-too-long
  else:
    report.add_ok(project)
