# Copyright 2025 Google LLC
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
"""Module containing Pub/Sub Push Delivery diagnostic tree and custom steps."""

from boltons.iterutils import get_path

from gcpdiag import runbook, utils
from gcpdiag.queries import apis, crm, monitoring, pubsub
from gcpdiag.runbook import op
from gcpdiag.runbook.pubsub import flags
from gcpdiag.runbook.pubsub import generalized_steps as pubsub_gs

RESPONSE_CODES = (
    'fetch pubsub_subscription '
    '| metric "pubsub.googleapis.com/subscription/push_request_count"'
    '| filter resource.project_id == "{project_id}"'
    ' && (resource.subscription_id == "{subscription_name}") '
    '| align rate(1m) '
    '| every 1m '
    '| group_by [metric.response_class], '
    ' [value_push_request_count_aggregate: aggregate(value.push_request_count)]'
    '| within 10m ')


class PushSubscriptionDelivery(runbook.DiagnosticTree):
  """Diagnostic checks for Cloud Pub/Sub push delivery issues.

  Provides a DiagnosticTree to check for issues related to delivery issues
  for subscriptions in Cloud Pub/Sub. Particularly this runbook focuses on common issues
  experienced while using Pub/Sub push subscriptions, including BQ & GCS subscriptions.

  - Areas:
    - subscription status
    - quotas
    - push responses
    - throughput rate
    - dead letter topic attachment and permissions
    - vpcsc enablement

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
    """Construct the diagnostic tree with appropriate steps."""
    start = PushSubscriptionDeliveryStart()
    self.add_start(start)

    active_check = pubsub_gs.ActiveSubscription()
    self.add_step(start, active_check)

    quota_check = pubsub_gs.PubsubQuotas()
    self.add_step(active_check, quota_check)

    end_point_responses = ResponseCodeStep()
    self.add_step(quota_check, end_point_responses)

    throughput = pubsub_gs.ThroughputQualification()
    self.add_step(end_point_responses, throughput)

    deadletter = pubsub_gs.DeadLetterTopic()
    self.add_step(throughput, deadletter)

    deadletter_permissions = pubsub_gs.DeadLetterTopicPermissions()
    self.add_step(deadletter, deadletter_permissions)

    self.add_step(deadletter_permissions, VpcScStep())

    # Ending your runbook
    self.add_end(PushSubscriptionDeliveryEnd())


class PushSubscriptionDeliveryStart(runbook.StartStep):
  """Start step of runbook.

  Gets the subscription and confirms it exists in the project.
  """

  def execute(self):
    """Start step"""
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
      if not subscription.is_push_subscription():
        op.add_skipped(
            resource=project,
            reason=
            ('Skipping execution because provided {subscription_name} is not a push subscription. '
             .format(subscription_name=subscription_name)),
        )


class ResponseCodeStep(runbook.Step):
  """Check push request responses from the endpoint.

  This step checks the responses coming from the endpoint and the
  success rates.
  """

  template = 'generics::endpoint_response'

  def execute(self):
    """Check push request responses from the endpoint"""
    project_id = op.get(flags.PROJECT_ID)

    push_metric = monitoring.query(
        project_id,
        RESPONSE_CODES.format(project_id=project_id,
                              subscription_name=op.get(
                                  flags.SUBSCRIPTION_NAME)),
    )
    if not push_metric:
      op.add_skipped(
          resource=crm.get_project(project_id),
          reason=(
              'Skipping as no traffic delivery to the endpoint has been detected'
          ))
    else:
      subscription = pubsub.get_subscription(project_id=project_id,
                                             subscription_name=op.get(
                                                 flags.SUBSCRIPTION_NAME))
      found_error_response: bool = False
      for metric_values in push_metric.values():
        response_class = get_path(metric_values,
                                  ('labels', 'metric.response_class'))
        if response_class != 'ack':
          found_error_response = True
          op.add_failed(resource=subscription,
                        reason=op.prep_msg(op.FAILURE_REASON),
                        remediation=op.prep_msg(op.FAILURE_REMEDIATION))
      if not found_error_response:
        op.add_ok(resource=subscription,
                  reason='No error responses from the endpoint detected')


class VpcScStep(runbook.Step):
  """Check if the VPC-SC api is enabled

  This step highlights caveats of using VPC-SC with push subscriptions
  """

  template = 'generics::vpcsc_api'

  def execute(self):
    """Check if push subscription project has a VPCSC perimeter """

    if apis.is_enabled(op.get(flags.PROJECT_ID), 'accesscontextmanager'):
      op.info(op.prep_msg(op.FAILURE_REMEDIATION), step_type='INFO')


class PushSubscriptionDeliveryEnd(runbook.EndStep):
  """End Step

    No more checks.
    """

  def execute(self):
    """End Step for push subscription"""
    op.info('No more checks to perform.')
