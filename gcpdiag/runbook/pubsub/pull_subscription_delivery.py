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
"""Module containing Pub/Sub Pull Delivery diagnostic tree and custom steps."""

from boltons.iterutils import get_path

from gcpdiag import runbook, utils
from gcpdiag.queries import apis, crm, monitoring, pubsub
from gcpdiag.runbook import op
from gcpdiag.runbook.pubsub import flags
from gcpdiag.runbook.pubsub import generalized_steps as pubsub_gs

DELIVERY_RATE = (
    'fetch pubsub_subscription | metric'
    ' "pubsub.googleapis.com/subscription/sent_message_count"| filter'
    ' resource.project_id == "{project_id}" && (resource.subscription_id =='
    ' "{subscription_name}") | '
    ' align rate(1m) | every 1m | group_by [],'
    ' [value_sent_message_count_aggregate: aggregate(value.sent_message_count)]'
    ' | within 10m')

UNACKED_MESSAGES = (
    'fetch pubsub_subscription | metric'
    ' "pubsub.googleapis.com/subscription/num_undelivered_messages" | filter'
    ' resource.project_id == "{project_id}" && (resource.subscription_id =='
    ' "{subscription_name}") | group_by 1m,'
    ' [value_num_undelivered_messages_mean:'
    ' mean(value.num_undelivered_messages)] | every 1m | group_by [],'
    ' [value_num_undelivered_messages_mean_aggregate:'
    ' aggregate(value_num_undelivered_messages_mean)] | within 10m')


class PullSubscriptionDelivery(runbook.DiagnosticTree):
  """Diagnostic checks for Cloud Pub/Sub pull delivery issues.

  Provides a DiagnosticTree to check for issues related to delivery issues
  for subscriptions in Cloud Pub/Sub. Particularly this runbook focuses on common issues
  experienced while using Pub/Sub pull subscriptions.

  - Areas:
    - delivery latency
    - quotas
    - pull rate
    - throughput rate
  """

  parameters = {
      flags.PROJECT_ID: {
          'type': str,
          'help': 'The Project ID of the resource under investigation',
          'required': True,
      },
      flags.SUBSCRIPTION_NAME: {
          'type': str,
          'help': ('The name of subscription to evaluate in the runbook'),
          'required': True,
      },
  }

  def build_tree(self):
    """Construct the Diagnostic Tree with appropriate steps."""
    # Instantiate your step classes
    start = PullSubscriptionDeliveryStart()
    self.add_start(start)

    quota_check = pubsub_gs.PubsubQuotas()
    self.add_step(start, quota_check)

    pull_rate = PullRate()
    self.add_step(quota_check, pull_rate)

    self.add_end(PullSubscriptionDeliveryEnd())


class PullSubscriptionDeliveryStart(runbook.StartStep):
  """Start step of runbook.

  Gets the subscription and confirms it exists in the project.
  """

  def execute(self):
    """Start step."""
    project = crm.get_project(op.get(flags.PROJECT_ID))
    if project:
      op.info(f'name: {project.name}, id: {project.id}')

    if not apis.is_enabled(op.get(flags.PROJECT_ID), 'pubsub'):
      op.add_skipped(
          project,
          reason='Pub/Sub API is not enabled, please enable to proceed.')
      return

    subscription_name = op.get(flags.SUBSCRIPTION_NAME)
    # check subscription exists and is pull
    try:
      subscription = pubsub.get_subscription(
          project_id=op.get(flags.PROJECT_ID),
          subscription_name=subscription_name)
    except utils.GcpApiError:
      op.add_skipped(
          resource=project,
          reason=
          ('Could not find subscription {subscription_name}, please confirm it exists or '
           'if recreated please wait a few minutes before querying the runbook'.
           format(subscription_name=subscription_name)),
      )
    else:
      if subscription.is_push_subscription():
        op.add_skipped(
            resource=project,
            reason=
            ('Skipping execution because provided {subscription_name} is a push subscription. '
             .format(subscription_name=subscription_name)),
        )


class PullRate(runbook.Gateway):
  """Has common step to check the high backlog vs the delivery rate ratio."""

  def execute(self):
    """Checks if delivery rate is low i.e. receiving fewer messages than expected."""
    subscription = pubsub.get_subscription(project_id=op.get(flags.PROJECT_ID),
                                           subscription_name=op.get(
                                               flags.SUBSCRIPTION_NAME))

    unacked_messages = self.unacked_messages(
        subscription.name)  # MQL takes truncated names
    delivery_rate = f'{self.delivery_rate(subscription.name):.2f}'

    op.info(message=(
        'The current rate of delivery rate is {delivery_rate}/s against'
        ' {unacked_messages} unacked messages. (Note that Pub/Sub may '
        'return fewer messages than the max'
        ' amount configured, in order to respond to pull RPCs in reasonable time.)'
    ).format(delivery_rate=delivery_rate, unacked_messages=unacked_messages))

    # analyze qualification
    self.add_child(child=pubsub_gs.ThroughputQualification())

  # subscription/sent_message_count
  def delivery_rate(self, subscription_name: str) -> float:
    delivery_rate_query = DELIVERY_RATE.format(
        project_id=op.get(flags.PROJECT_ID),
        subscription_name=subscription_name)
    time_series = monitoring.query(op.get(flags.PROJECT_ID),
                                   delivery_rate_query)
    if time_series:
      return float(get_path(list(time_series.values())[0], 'values')[0][-1])
    return 0.0

  # subscription/num_undelivered_messages
  def unacked_messages(self, subscription_name: str) -> float:
    unacked_messages_query = UNACKED_MESSAGES.format(
        project_id=op.get(flags.PROJECT_ID),
        subscription_name=subscription_name)

    time_series = monitoring.query(op.get(flags.PROJECT_ID),
                                   unacked_messages_query)
    if time_series:
      return float(get_path(list(time_series.values())[0], 'values')[0][0])
    return 0.0


class PullSubscriptionDeliveryEnd(runbook.EndStep):
  """End of this runbook.

  No more checks to perform.
  """

  def execute(self):
    """End step. """
    op.info('No more checks to perform.')
