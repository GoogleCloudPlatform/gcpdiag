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
"""Pub/Sub service account has GCS permissions if GCS subscription(s) exist.

For any GCS subscriptions to deliver messages successfully, they should
have the appropriate permissions at the project or bucket level.
"""

import re
from typing import Dict

from gcpdiag import lint, models
from gcpdiag.queries import crm, gcs, iam, pubsub

policies: Dict[str, Dict] = {'projects': {}, 'buckets': {}}
ROLE_GCS_STORAGE_ADMIN = 'roles/storage.admin'
ROLE_LEGACY_BUCKET_READER = 'roles/storage.legacyBucketReader'
ROLE_OBJECT_CREATOR = 'roles/storage.objectCreator'


def prefetch_rule(context: models.Context):
  """Collect project & unique bucket policies."""
  policies['projects'][context.project_id] = iam.get_project_policy(context)

  gcs_subscription_buckets = set()
  subscriptions = pubsub.get_subscriptions(context)

  if subscriptions:
    for _, subscription in subscriptions.items():
      if subscription.is_gcs_subscription():
        gcs_subscription_buckets.add(subscription.gcs_subscription_bucket())

  if gcs_subscription_buckets:
    for bucket in gcs_subscription_buckets:
      policies['buckets'][bucket] = gcs.get_bucket_iam_policy(context, bucket)


def run_rule(context: models.Context, report: lint.LintReportRuleInterface):
  """Check if subscription has relevant GCS permissions."""

  project = crm.get_project(context.project_id)
  project_nr = crm.get_project(context.project_id).number

  if not policies['buckets']:
    report.add_skipped(None, 'no GCS subscriptions found')
  else:
    service_account_re = re.compile('serviceAccount:service-' +
                                    str(project_nr) +
                                    '@gcp-sa-pubsub.iam.gserviceaccount.com')
    member = next(
        filter(
            service_account_re.match,
            policies['projects'][context.project_id].get_members(),
        ),
        None,
    )

    if not member:
      report.add_failed(project, 'no Pub/Sub Service Account found')
    # Check at project level for role_gcs_storage_admin
    # and at bucket level for all(role_legacy_bucket_reader,role_object_creator)
    elif not check_policy_project(context,
                                  member) and not check_policy_buckets(member):
      report.add_failed(
          project,
          f'{member} does not have GCS subscription permissions for the role',
      )
    else:
      report.add_ok(project)


def check_policy_project(context, member) -> bool:
  """Check if a member is assigned the (one) apt role at project level."""
  if not policies['projects'][context.project_id].has_role_permissions(
      member, ROLE_GCS_STORAGE_ADMIN):
    return False
  return True


def check_policy_buckets(member) -> bool:
  """Check if a member is assigned the (two) apt roles at bucket level."""
  for bucket_policy in policies['buckets'].values():
    if not bucket_policy.has_role_permissions(
        member,
        ROLE_LEGACY_BUCKET_READER) or not bucket_policy.has_role_permissions(
            member, ROLE_OBJECT_CREATOR):
      return False
  return True
