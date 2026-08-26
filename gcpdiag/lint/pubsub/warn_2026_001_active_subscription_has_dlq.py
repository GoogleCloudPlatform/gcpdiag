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

# Lint as: python3
"""Active Pub/Sub subscriptions have a Dead-Letter Queue configured.

Active Pub/Sub subscriptions should have a Dead-Letter Queue (DLQ) configured
to prevent head-of-line delivery delays and runaway storage billing costs caused
by un-acknowledged poison messages.
"""

from gcpdiag import lint, models
from gcpdiag.queries import apis, crm, pubsub

MAX_SUBSCRIPTIONS_TO_DISPLAY = 20


def prefetch_rule(context: models.Context):
  """Prefetch subscriptions for parallel performance."""
  if apis.is_enabled(context.project_id, 'pubsub'):
    pubsub.get_subscriptions(context)


def run_rule(context: models.Context, report: lint.LintReportRuleInterface):
  """Active Pub/Sub subscriptions have a Dead-Letter Queue configured."""
  project = crm.get_project(context.project_id)
  if not apis.is_enabled(context.project_id, 'pubsub'):
    report.add_skipped(project, 'Pub/Sub API is disabled')
    return

  subscriptions = pubsub.get_subscriptions(context)

  if not subscriptions:
    report.add_skipped(project, 'No subscriptions found')
    return

  has_active_subs = False
  failing_subs = []

  # Sort by name for deterministic reporting output
  for _, subscription in sorted(subscriptions.items()):
    if not subscription.is_active():
      continue

    if subscription.is_detached():
      continue

    has_active_subs = True
    if not subscription.has_dead_letter_topic():
      failing_subs.append(subscription.name)

  if not has_active_subs:
    report.add_skipped(project, 'No active subscriptions found')
    return

  if failing_subs:
    extra_subs = ''
    if len(failing_subs) > MAX_SUBSCRIPTIONS_TO_DISPLAY:
      extra_subs = f', and {len(failing_subs) - MAX_SUBSCRIPTIONS_TO_DISPLAY} more subscriptions'

    report.add_failed(
      project,
      reason=(
        f'{len(failing_subs)} subscriptions do not have a Dead-Letter Queue (DLQ) configured: '
        f'{", ".join(failing_subs[:MAX_SUBSCRIPTIONS_TO_DISPLAY])}{extra_subs}'
      ),
    )
  else:
    report.add_ok(project)
