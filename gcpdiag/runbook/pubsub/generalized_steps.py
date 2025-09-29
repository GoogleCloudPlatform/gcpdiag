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
"""Common steps for Pub/Sub runbooks."""

import re

from boltons.iterutils import get_path

from gcpdiag import runbook
from gcpdiag.queries import crm, iam, monitoring, pubsub, quotas
from gcpdiag.runbook import op
from gcpdiag.runbook.pubsub import flags


class PubsubQuotas(runbook.Step):
  """Has common step to check if any Pub/Sub quotas are being exceeded in the project.

  This step checks if any quotas have been exceeded.
  """

  template = 'generics::quota_exceeded'

  def execute(self):
    """Checks if any Pub/Sub quotas are being exceeded."""
    if self.quota_exceeded_found is True:
      op.add_failed(
          resource=crm.get_project(op.get(flags.PROJECT_ID)),
          reason=op.prep_msg(op.FAILURE_REASON),
          remediation=op.prep_msg(op.FAILURE_REMEDIATION),
      )
    else:
      op.add_ok(
          resource=crm.get_project(op.get(flags.PROJECT_ID)),
          reason='Quota usage is within project limits.',
      )

  def quota_exceeded_found(self) -> bool:
    quota_exceeded_query = (
        quotas.QUOTA_EXCEEDED_HOURLY_PER_SERVICE_QUERY_TEMPLATE.format(
            service_name='pubsub', within_days=1))
    time_series = monitoring.query(op.get(flags.PROJECT_ID),
                                   quota_exceeded_query)
    if time_series:
      return True
    return False


class ThroughputQualification(runbook.Step):
  """Has common step to validate subscription qualification attributes.

  This step checks if the throughput qualification is in a good state.
  """

  template = 'generics::throughput_qualification'

  def execute(self):
    """Checks if subscription has good health (high qualification)."""

    subscription = pubsub.get_subscription(project_id=op.get(flags.PROJECT_ID),
                                           subscription_name=op.get(
                                               flags.SUBSCRIPTION_NAME))

    qualification_query = (
        'fetch pubsub_subscription | metric'
        ' "pubsub.googleapis.com/subscription/delivery_latency_health_score" |'
        ' filter (resource.subscription_id =="{}") | group_by 1m,'
        ' [value_delivery_latency_health_score_sum:sum(if(value.delivery_latency_health_score,'
        ' 1, 0))] | every 1m | within 10m').format(subscription.name)

    low_health_metrics = []
    time_series = monitoring.query(op.get(flags.PROJECT_ID),
                                   qualification_query)
    for metric in list(time_series.values()):
      # metric_dict[get_path(metric, ('labels','metric.criteria'))] = metric['values']
      if metric['values'][0][-1] == 0:
        low_health_metrics.append(
            get_path(metric, ('labels', 'metric.criteria')))

    if low_health_metrics:
      op.add_failed(
          resource=subscription,
          reason=op.prep_msg(op.FAILURE_REASON,
                             low_health_metrics=low_health_metrics),
          remediation=op.prep_msg(op.FAILURE_REMEDIATION),
      )
    else:
      op.add_ok(resource=subscription, reason='Subcription has good health')


class ActiveSubscription(runbook.Step):
  """Has common step to validate if the subscription is active.

  This step checks if the subscription is in active (valid) state.
  """

  template = 'generics::subscription_state'

  def execute(self):
    """Checks subscription activity status."""
    subscription = pubsub.get_subscription(project_id=op.get(flags.PROJECT_ID),
                                           subscription_name=op.get(
                                               flags.SUBSCRIPTION_NAME))
    if subscription.is_active():
      op.add_ok(resource=subscription, reason='Subscription is active')
    else:
      op.add_failed(resource=subscription,
                    reason='Inactive subscription. ',
                    remediation=op.prep_msg(op.FAILURE_REMEDIATION))


class DeadLetterTopic(runbook.Step):
  """Has common step to check if the subscription has a dead letter topic.

  This step checks if the subscription has a Dead Letter Topic attached.
  This is important to remove the messages that have failed processing out of the
  main subscription.
  """

  template = 'generics::dead_letter_topic'

  def execute(self):
    """Checks for dead letter topic presence."""
    subscription = pubsub.get_subscription(project_id=op.get(flags.PROJECT_ID),
                                           subscription_name=op.get(
                                               flags.SUBSCRIPTION_NAME))
    if subscription.has_dead_letter_topic():
      op.add_ok(resource=subscription,
                reason='Dead letter topic already attached')
    else:
      op.add_failed(resource=subscription,
                    reason=op.prep_msg(op.FAILURE_REASON),
                    remediation=op.prep_msg(op.FAILURE_REMEDIATION))


class DeadLetterTopicPermissions(runbook.Step):
  """"Verifies that the Pub/Sub service agent has the necessary IAM permissions \
  for the configured Dead Letter Topic.

  This step checks if the pubsub agent has the relevant permissions to move
  messages whose processing has failed continuously to the dead letter topic.
  """

  template = 'generics::dead_letter_topic_permissions'

  def execute(self):
    """Checks for dead letter topic permissions."""
    project_id = op.get(flags.PROJECT_ID)
    project = crm.get_project(project_id=project_id)
    subscription = pubsub.get_subscription(
        project_id=project_id,
        subscription_name=op.get(flags.SUBSCRIPTION_NAME),
    )
    # dead letter topic is in another project that the user may not be allowed
    if subscription.has_dead_letter_topic() and subscription.dead_letter_topic(
    ).split('/')[1] != project_id:
      op.info(
          'Dead Letter topic permissions could not be verified. ' \
          'Please ensure both the publisher role to the dead letter topic/project ' \
          'level and the subscriber role at the subscription/project level to the ' \
          'pubsub agent ' \
          'serviceAccount:service-<project-number>@gcp-sa-pubsub.iam.gserviceaccount.com ' \
          'are assigned'
      )
      op.add_skipped(resource=project,
                     reason='Dead Letter topic is in another project.')
      return

    role_publisher = 'roles/pubsub.publisher'
    role_subscriber = 'roles/pubsub.subscriber'
    policy = iam.get_project_policy(op.get_context())
    service_account_re = re.compile('serviceAccount:service-' +
                                    str(project.number) +
                                    '@gcp-sa-pubsub.iam.gserviceaccount.com')

    service_account = next(
        filter(
            service_account_re.match,
            policy.get_members(),
        ),
        None,
    )

    if not service_account:
      op.add_skipped(resource=project, reason='no Pub/Sub Service Agent found')
      return

    # check at the project level
    if policy.has_role_permissions(
        member=service_account,
        role=role_subscriber) and policy.has_role_permissions(
            member=service_account, role=role_publisher):
      op.add_ok(resource=project,
                reason='Dead Letter permissions assigned at the project level')
      return

    # check at the resource level
    subscription_policy = pubsub.get_subscription_iam_policy(
        op.get_context(), subscription.full_path)
    topic_policy = pubsub.get_topic_iam_policy(op.get_context(),
                                               subscription.dead_letter_topic())

    # log uncertain in case of fine grained access restrictions
    if not subscription_policy.has_role_permissions(
        service_account,
        role_subscriber) or not topic_policy.has_role_permissions(
            service_account, role_publisher):
      op.add_uncertain(
          resource=project,
          reason='Missing dead letter topic permissions',
          remediation=
          'Please ensure both the publisher role to the dead letter topic/project ' \
          'level and the subscriber role at the subscription/project level to the ' \
          'pubsub agent {} are assigned'
          .format(service_account))
    else:
      op.add_ok(resource=subscription,
                reason='Dead letter topic permissions assigned')
