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
"""Push delivery requests for push subscriptions are not failing.

For any push subscription, delivery to the endpoint should return an ack
response for successfully processed messages.
"""

from itertools import islice
from typing import Dict

from boltons.iterutils import get_path

from gcpdiag import lint, models
from gcpdiag.queries import crm, monitoring, pubsub

push_request_count: Dict[str, monitoring.TimeSeriesCollection] = {}
DURATION = '10m'  # 10 minutes - also used to measure delivery latency health
MAX_SUBSCRIPTIONS_TO_DISPLAY = 10


def prefetch_rule(context: models.Context):
  subscription_name = ''
  query_push_request_count = (
      'fetch pubsub_subscription| metric'
      ' "pubsub.googleapis.com/subscription/push_request_count"| filter'
      ' resource.project_id == "{}" &&'
      ' (resource.subscription_id == "{}") | align rate(1m)|'
      ' every 1m| group_by'
      ' [metric.response_class],[value_push_request_count_aggregate:'
      ' aggregate(value.push_request_count)] | within {}')

  subscriptions = pubsub.get_subscriptions(context)

  for _, subscription in subscriptions.items():
    if subscription.is_push_subscription():
      subscription_name = subscription.name
      push_request_count[subscription_name] = monitoring.query(
          context.project_id,
          query_push_request_count.format(context.project_id, subscription_name,
                                          DURATION),
      )


def run_rule(context: models.Context, report: lint.LintReportRuleInterface):
  project = crm.get_project(context.project_id)

  if not push_request_count:
    report.add_skipped(None, 'no subscription metrics found')

  failing_subs = set()
  for subscription_name, push_metric in push_request_count.items():
    if (not push_metric
       ):  # empty for subscription without traffic for the duration
      continue
    else:
      for metric_values in push_metric.values():
        # one of ['ack', 'deadline_exceeded', 'internal', 'invalid',
        # 'remote_server_4xx', 'remote_server_5xx', 'unreachable']
        response_class = get_path(metric_values,
                                  ('labels', 'metric.response_class'))

        if response_class != 'ack':
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
        f'{len(failing_subs)} subscriptions have non-ack responses'
        ' from the endpoint:'
        f" {', '.join(islice(failing_subs, MAX_SUBSCRIPTIONS_TO_DISPLAY))}{extra_subs}",
    )
  # pylint: enable=line-too-long
  else:
    report.add_ok(project)
