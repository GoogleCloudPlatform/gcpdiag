# Copyright 2024 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Pub/Sub push subscription service agent has the Service Account Token Creator Role.

The Pub/Sub service agent
(service-{project-number}@gcp-sa-pubsub.iam.gserviceaccount.com) requires the
Service Account Token Creator Role (roles/iam.serviceAccountTokenCreator)
on the service account configured for a push subscription with authentication
enabled. This allows Pub/Sub to generate tokens for authenticating to the
push endpoint.
"""
from gcpdiag import lint, models
from gcpdiag.queries import crm, iam, pubsub

TOKEN_CREATOR_ROLE = 'roles/iam.serviceAccountTokenCreator'
PUBSUB_SERVICE_AGENT_ROLE = 'roles/pubsub.serviceAgent'
subscriptions = {}


def prefetch_rule(context: models.Context):
  subscriptions[context.project_id] = pubsub.get_subscriptions(context)


def run_rule(context: models.Context, report: lint.LintReportRuleInterface):
  """Run the rule."""
  project = crm.get_project(context.project_id)
  project_subscriptions = subscriptions.get(context.project_id)

  if not project_subscriptions:
    report.add_skipped(project, 'no Pub/Sub subscriptions found')
    return

  project_number = crm.get_project(context.project_id).number
  pubsub_service_agent = (
      f'serviceAccount:service-{project_number}@gcp-sa-pubsub.iam.gserviceaccount.com'
  )
  project_iam_policy = iam.get_project_policy(context.project_id)

  for sub in project_subscriptions.values():
    if not sub.is_push_subscription() or 'oidcToken' not in sub.push_config:
      report.add_ok(sub)
      continue

    service_account_email = sub.push_config['oidcToken']['serviceAccountEmail']
    sa_iam_policy = iam.get_service_account_iam_policy(
        project_id=context.project_id, service_account=service_account_email)

    has_permission = sa_iam_policy.has_role_permissions(
        pubsub_service_agent,
        TOKEN_CREATOR_ROLE) or project_iam_policy.has_role_permissions(
            pubsub_service_agent, TOKEN_CREATOR_ROLE)

    if not has_permission:
      report.add_failed(
          sub,
          (f'The Pub/Sub service agent ({pubsub_service_agent}) is missing the'
           f' {TOKEN_CREATOR_ROLE} role on the service account'
           f' {service_account_email} or on the project.'),
      )
    else:
      report.add_ok(sub)
