# Copyright 2025 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Runbook for troubleshooting BigQuery subscriptions."""

from boltons.iterutils import get_path

from gcpdiag import runbook, utils
from gcpdiag.queries import apis, bigquery, crm, iam, monitoring, pubsub
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


class BigquerySubscriptionDelivery(runbook.DiagnosticTree):
  """Troubleshoot BigQuery Subscription Errors

A diagnostic guide to help you resolve common issues
causing message delivery failures from Pub/Sub to BigQuery.
  """
  parameters = {
      flags.PROJECT_ID: {
          'type': str,
          'help': 'The Project ID of the resource under investigation',
          'required': True
      },
      flags.SUBSCRIPTION_NAME: {
          'type': str,
          'help': 'The Pub/Sub subscription ID',
          'required': True
      },
      'table_id': {
          'type': str,
          'help':
              ('The BigQuery table ID in the format "project_id:dataset.table" '
               'or "dataset.table"'),
          'required': True
      }
  }

  def build_tree(self):
    """Construct the diagnostic tree with appropriate steps."""
    start = StartStep()
    self.add_start(start)

    subscription_check = SubscriptionExistenceCheck()
    self.add_step(parent=start, child=subscription_check)

    table_check = BigQueryTableExistenceCheck()
    self.add_step(parent=subscription_check, child=table_check)

    permission_check = BigQueryWriterPermissionCheck()
    self.add_step(parent=table_check, child=permission_check)

    subscription_status_check = SubscriptionStatusCheck(
        is_push_subscription=True)
    self.add_step(parent=permission_check, child=subscription_status_check)

    quota_check = pubsub_gs.PubsubQuotas()
    self.add_step(subscription_status_check, quota_check)

    investigate_push_errors = InvestigateBQPushErrors()
    self.add_step(parent=quota_check, child=investigate_push_errors)

    throughput = pubsub_gs.ThroughputQualification()
    self.add_step(investigate_push_errors, throughput)

    dlq_check = pubsub_gs.DeadLetterTopic()
    self.add_step(throughput, dlq_check)

    dlq_check_permissions = pubsub_gs.DeadLetterTopicPermissions()
    self.add_step(dlq_check, dlq_check_permissions)

    self.add_end(EndStep())


class StartStep(runbook.StartStep):
  """Check that the project exists and is reachable."""
  template = 'generics::start'

  def execute(self):
    """Check that the project exists and Pub/Sub API is enabled."""
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


class SubscriptionExistenceCheck(runbook.Step):
  """Check that the Pub/Sub subscription exists."""
  template = 'generics::subscription_existence'

  def execute(self):
    """Check that the Pub/Sub subscription exists."""
    subscription = None
    try:
      subscription = pubsub.get_subscription(op.get(flags.PROJECT_ID),
                                             op.get(flags.SUBSCRIPTION_NAME))
    except utils.GcpApiError as err:
      if 'Resource not found' in err.message:
        op.add_failed(resource=subscription,
                      reason=op.prep_msg(op.FAILURE_REASON,
                                         subscription_name=op.get(
                                             flags.SUBSCRIPTION_NAME)),
                      remediation=op.prep_msg(op.FAILURE_REMEDIATION))
        return
      else:
        raise

    if not subscription:
      op.add_failed(resource=subscription,
                    reason=op.prep_msg(op.FAILURE_REASON,
                                       subscription_name=op.get(
                                           flags.SUBSCRIPTION_NAME)),
                    remediation=op.prep_msg(op.FAILURE_REMEDIATION))
    else:
      op.add_ok(subscription,
                reason=f"Pub/Sub subscription '{subscription.name}' found.")


class BigQueryTableExistenceCheck(runbook.Step):
  """Check that the BigQuery table exists."""
  template = 'generics::bq_table_existence'

  def execute(self):
    """Check that the BigQuery table exists."""
    project_id = op.get(flags.PROJECT_ID)
    table_full_id = op.get('table_id')
    if ':' in table_full_id:
      project_id, table_id = table_full_id.split(':', 1)
    else:
      table_id = table_full_id
    try:
      dataset_id, table_name = table_id.split('.', 1)
    except ValueError:
      op.add_failed(resource=None,
                    reason=op.prep_msg(op.FAILURE_REASON,
                                       table_full_id=table_full_id),
                    remediation=op.prep_msg(op.FAILURE_REMEDIATION))
      return

    table = bigquery.get_table(project_id, dataset_id, table_name)
    if not table:
      op.add_failed(resource=None,
                    reason=op.prep_msg(op.FAILURE_REASON,
                                       table_full_id=table_full_id),
                    remediation=op.prep_msg(op.FAILURE_REMEDIATION))
    else:
      op.add_ok(
          resource=None,
          reason=f'BigQuery table {table_full_id} found.',
      )


class BigQueryWriterPermissionCheck(runbook.Step):
  """Check that the Pub/Sub service agent has writer permissions on the table."""
  template = 'generics::permission_check'

  def execute(self):
    """Check that the Pub/Sub service agent has writer permissions."""
    project = crm.get_project(op.get(flags.PROJECT_ID))
    table_full_id = op.get('table_id')
    if ':' in table_full_id:
      table_project_id, table_id = table_full_id.split(':', 1)
    else:
      table_project_id = op.get(flags.PROJECT_ID)
      table_id = table_full_id
    try:
      dataset_id, table_name = table_id.split('.', 1)
    except ValueError:
      # Handled in BigQueryTableExistenceCheck
      return

    service_account = \
        f'serviceAccount:service-{project.number}@gcp-sa-pubsub.iam.gserviceaccount.com'

    table_policy = bigquery.get_table(table_project_id, dataset_id, table_name)
    if not table_policy:
      # table not found, handled in previous step
      return

    project_policy = iam.get_project_policy(op.get_context())
    required_permissions = {
        'bigquery.tables.updateData', 'bigquery.tables.getData'
    }
    has_permissions = all(
        project_policy.has_permission(service_account, p)
        for p in required_permissions)

    if not has_permissions:
      op.add_failed(resource=None,
                    reason=op.prep_msg(op.FAILURE_REASON,
                                       service_account=service_account,
                                       project_id=project),
                    remediation=op.prep_msg(op.FAILURE_REMEDIATION,
                                            service_account=service_account))
    else:
      op.add_ok(
          resource=None,
          reason=
          'Pub/Sub service account has permissions to write to the BigQuery table.'
      )


class SubscriptionStatusCheck(runbook.Step):
  """Check the status of the BigQuery subscription."""
  template = 'generics::subscription_status'

  def execute(self):
    """Check the BigQuery subscription status and look for common issues."""
    try:
      subscription = pubsub.get_subscription(op.get(flags.PROJECT_ID),
                                             op.get(flags.SUBSCRIPTION_NAME))
    except ValueError:
      # Handled in SubscriptionExistenceCheck
      return

    if subscription.is_active():
      op.add_ok(resource=subscription,
                reason=f'The subscription {subscription} state is ACTIVE.')
    else:
      op.add_failed(
          resource=subscription,
          reason=f'The Subscription {subscription} is not in an ACTIVE state.',
          remediation=op.prep_msg(op.FAILURE_REMEDIATION))


class InvestigateBQPushErrors(runbook.Step):
  """Investigate message backlog issues for BigQuery subscriptions using push metrics."""

  template = 'generics::invalid'

  def execute(self):
    """Check push request responses from BigQuery for issues."""
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
              'Skipping as no traffic delivery to the BigQuery has been detected'
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
                  reason='No error responses from BigQuery detected')


class EndStep(runbook.EndStep):
  """Finalizing the runbook."""

  def execute(self):
    """Finalizing the runbook."""
    op.info('Finished troubleshooting BigQuery subscriptions.')
