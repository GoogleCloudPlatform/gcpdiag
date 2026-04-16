# Copyright 2026 Google LLC
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
"""Runbook for troubleshooting Pub/Sub Cloud Storage subscriptions"""

from boltons.iterutils import get_path

from gcpdiag import models, runbook, utils
from gcpdiag.queries import apis, crm, gcs, monitoring, pubsub
from gcpdiag.runbook import op
from gcpdiag.runbook.pubsub import flags
from gcpdiag.runbook.pubsub import generalized_steps as pubsub_gs

# Query to fetch push request counts grouped by response_class
RESPONSE_CODES = (
    'fetch pubsub_subscription '
    '| metric "pubsub.googleapis.com/subscription/push_request_count"'
    '| filter resource.project_id == "{project_id}"'
    ' && (resource.subscription_id == "{subscription_name}") '
    '| align rate(1m) '
    '| every 1m '
    '| group_by [metric.response_class], '
    ' [value_push_request_count_aggregate: aggregate(value.push_request_count)]'
    '| within 30m ')


class GcsSubscriptionDelivery(runbook.DiagnosticTree):
  """Troubleshoot Pub/Sub to Cloud Storage subscription issues.

  This runbook checks for common configuration problems with Pub/Sub subscriptions
  that are set up to write directly to a Google Cloud Storage bucket.

  Checks performed:
  - Subscription existence and type.
  - Cloud Storage bucket existence.
  - IAM permissions for the Pub/Sub service account on the bucket.
  - State of the Pub/Sub subscription.
  """
  parameters = {
      flags.PROJECT_ID: {
          'type': str,
          'help': 'The Project ID containing the Pub/Sub subscription',
          'required': True
      },
      flags.SUBSCRIPTION_NAME: {
          'type': str,
          'help': 'The Pub/Sub subscription ID',
          'required': True
      }
  }

  def build_tree(self):
    """Construct the diagnostic tree with appropriate steps."""
    start = GcsSubscriptionDeliveryStart()
    self.add_start(start)

    subscription_check = GcsSubscriptionExistenceCheck()
    self.add_step(parent=start, child=subscription_check)

    check_bucket = CheckGcsBucket()
    self.add_step(parent=subscription_check, child=check_bucket)

    check_permissions = CheckServiceAccountPermissions()
    self.add_step(parent=check_bucket, child=check_permissions)

    quota_check = pubsub_gs.PubsubQuotas()
    self.add_step(check_permissions, quota_check)

    end_point_responses = ResponseCodeStep()
    self.add_step(quota_check, end_point_responses)

    check_sub_state = pubsub_gs.ActiveSubscription()
    self.add_step(parent=end_point_responses, child=check_sub_state)

    throughput = pubsub_gs.ThroughputQualification()
    self.add_step(check_sub_state, throughput)

    deadletter = pubsub_gs.DeadLetterTopic()
    self.add_step(throughput, deadletter)

    deadletter_permissions = pubsub_gs.DeadLetterTopicPermissions()
    self.add_step(deadletter, deadletter_permissions)

    self.add_end(GcsSubscriptionDeliveryEnd())


class GcsSubscriptionDeliveryStart(runbook.StartStep):
  """Start GCS Subscription check

  Check that the project exists and is reachable.
  """

  template = 'generics::start'

  def execute(self):
    """Check that the project exists and Pub/Sub API is enabled"""
    try:
      project = crm.get_project(op.get(flags.PROJECT_ID))
      if not project:
        op.add_failed(resource=None,
                      reason=op.prep_msg(op.FAILURE_REASON),
                      remediation=op.prep_msg(op.FAILURE_REMEDIATION))
        return
      else:
        op.add_ok(project, reason=f"Project '{project.id}' found.")
    except utils.GcpApiError:
      op.add_failed(resource=None,
                    reason=op.prep_msg(op.FAILURE_REASON,
                                       project_id=op.get(flags.PROJECT_ID)),
                    remediation=op.prep_msg(op.FAILURE_REMEDIATION))
      return
    if not apis.is_enabled(op.get(flags.PROJECT_ID), 'pubsub'):
      op.add_skipped(
          project,
          reason='Pub/Sub API is not enabled, please enable to proceed.')
      return


class GcsSubscriptionExistenceCheck(runbook.Step):
  """Check that the Pub/Sub subscription exists.

  This step checks that the Pub/Sub subscription exists and is a gcs subscription.
  """

  template = 'generics::subscription_existence'

  def execute(self):
    """Check that the Pub/Sub subscription exists."""
    try:
      project_id = op.get(flags.PROJECT_ID)
      subscription_id = op.get(flags.SUBSCRIPTION_NAME)
      subscription = pubsub.get_subscription(project_id, subscription_id)
    except utils.GcpApiError:
      op.add_failed(resource=None,
                    reason=op.prep_msg(op.FAILURE_REASON,
                                       subscription_name=op.get(
                                           flags.SUBSCRIPTION_NAME)),
                    remediation=op.prep_msg(op.FAILURE_REMEDIATION))
      return

    if not subscription.is_gcs_subscription:
      op.add_failed(resource=subscription,
                    reason=op.prep_msg(op.FAILURE_REASON,
                                       subscription_name=op.get(
                                           flags.SUBSCRIPTION_NAME)),
                    remediation=op.prep_msg(op.FAILURE_REMEDIATION))
    else:
      op.add_ok(
          subscription,
          reason=(
              f'Subscription {subscription_id} is a Cloud Storage subscription'
              f'targeting bucket: {subscription.gcs_subscription_bucket()}'))


class CheckGcsBucket(runbook.Step):
  """Checks if the target Cloud Storage bucket exists.

  This step checks if the target Cloud Storage bucket exists.
  """

  template = 'generics::gcs_bucket_existence'

  def execute(self):
    """Checking Cloud Storage bucket existence"""
    subscription = pubsub.get_subscription(op.get(flags.PROJECT_ID),
                                           op.get(flags.SUBSCRIPTION_NAME))
    bucket_name = subscription.gcs_subscription_bucket()
    context = models.Context(project_id=op.get(flags.PROJECT_ID))
    if not bucket_name:
      op.add_failed(resource=None,
                    reason=op.prep_msg(op.FAILURE_REASON),
                    remediation=op.prep_msg(op.FAILURE_REMEDIATION))
      return

    try:
      bucket = gcs.get_bucket(context, bucket_name)
      if bucket:
        op.add_ok(bucket, reason=f'Target bucket {bucket_name} exists.')
      else:
        op.add_failed(resource=None,
                      reason=op.prep_msg(op.FAILURE_REASON),
                      remediation=op.prep_msg(op.FAILURE_REMEDIATION))
    except utils.GcpApiError:
      op.add_failed(resource=None,
                    reason=op.prep_msg(op.FAILURE_REASON),
                    remediation=op.prep_msg(op.FAILURE_REMEDIATION))


class CheckServiceAccountPermissions(runbook.Step):
  """Checks if the Pub/Sub service account has correct permissions on the bucket.

  This step checks if the Pub/Sub service account has correct permissions on the bucket
  """

  template = 'generics::gcs_permission_check'

  def execute(self):
    """Checking Pub/Sub service account permissions on the bucket"""
    project_id = op.get(flags.PROJECT_ID)
    subscription = pubsub.get_subscription(project_id,
                                           op.get(flags.SUBSCRIPTION_NAME))
    bucket_name = subscription.gcs_subscription_bucket()
    context = models.Context(project_id=project_id)

    if not bucket_name:
      op.add_skipped(
          None, reason='Bucket name not found, skipping permission checks.')
      return

    project = crm.get_project(project_id)
    service_account = \
    f'serviceAccount:service-{project.number}@gcp-sa-pubsub.iam.gserviceaccount.com'

    required_permissions = ['storage.objects.create', 'storage.buckets.get']

    try:
      policy = gcs.get_bucket_iam_policy(context, bucket_name)
      has_permissions = all(
          policy.has_permission(service_account, p)
          for p in required_permissions)

    except utils.GcpApiError as e:
      op.add_uncertain(
          subscription,
          reason=
          f'Could not verify IAM permissions on bucket {bucket_name}. Error: {e}',
          remediation=
          ('Please ensure you have permissions to get the bucket\'s IAM policy '
           '(`storage.buckets.getIamPolicy`) and check manually.'))
      return

    if has_permissions:
      op.add_ok(
          subscription,
          reason=
          (f'Pub/Sub service account {service_account} has the necessary permissions '
           f'on bucket {bucket_name}.'))
    else:
      op.add_failed(resource=None,
                    reason=op.prep_msg(op.FAILURE_REASON,
                                       service_account=service_account,
                                       bucket_name=bucket_name),
                    remediation=op.prep_msg(op.FAILURE_REMEDIATION,
                                            service_account=service_account,
                                            bucket_name=bucket_name))


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


class GcsSubscriptionDeliveryEnd(runbook.EndStep):
  """End Step

  No more checks.
  """

  def execute(self):
    """Summarizing the findings"""
    project_id = op.get(flags.PROJECT_ID)
    subscription_id = op.get(flags.SUBSCRIPTION_NAME)
    op.info(
        f'Finished checks for Pub/Sub to GCS subscription' \
          f'{subscription_id} in project {project_id}.'
    )
    op.info(
        'Please review the check results above. If issues persist, ' \
        'check Cloud Logging for errors related to the subscription.'
    )
