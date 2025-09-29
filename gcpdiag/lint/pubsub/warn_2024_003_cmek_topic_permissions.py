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
"""Pub/Sub service account has the Encrypter and Decrypter Role if CMEK exist.

As long as the service account has the CyptoKey Encrypter/Decrypter role, the
service can encrypt and decrypt its data. If you revoke this role, or if you
disable or destroy the CMEK key, that data can't be accessed.
"""

import re

from gcpdiag import lint, models
from gcpdiag.queries import apis, crm, iam, pubsub

role_encrypter_decrypter = 'roles/cloudkms.cryptoKeyEncrypterDecrypter'

policy_by_project = {}
projects = {}


def prefetch_rule(context: models.Context):
  projects[context.project_id] = crm.get_project(context.project_id)
  policy_by_project[context.project_id] = iam.get_project_policy(context)


def run_rule(context: models.Context, report: lint.LintReportRuleInterface):
  """Check if the topic has CMEK ."""

  if not apis.is_enabled(context.project_id, 'pubsub'):
    report.add_skipped(None, 'PubSub is disabled')
    return

  if not apis.is_enabled(context.project_id, 'cloudkms'):
    report.add_skipped(None, 'CloudKMS api is disabled')
    return

  topics = pubsub.get_topics(context)

  if not topics:
    report.add_skipped(None, 'no topics found')
    return

  project = projects[context.project_id]
  required_permission = True
  customer_encryption_key_exist = False
  for _, topic in topics.items():
    try:
      kms_key = topic.kms_key_name.split('/')
      if context.project_id == kms_key[1]:
        customer_encryption_key_exist = True
        break
    except KeyError:
      continue

  if not customer_encryption_key_exist:
    report.add_skipped(None, 'no customer managed encryption topic found')
  else:
    project_policy = policy_by_project[context.project_id]
    service_account_re = re.compile('serviceAccount:service-' +
                                    str(project.number) +
                                    '@gcp-sa-pubsub.iam.gserviceaccount.com')
    service_account = next(
        filter(
            service_account_re.match,
            project_policy.get_members(),
        ),
        None,
    )

    if not service_account:
      report.add_failed(project, 'no Pub/Sub Service Account found')

    if not project_policy.has_role_permissions(service_account,
                                               role_encrypter_decrypter):
      report.add_failed(
          project,
          f'{service_account}\nmissing role: {role_encrypter_decrypter}',
      )
      required_permission = False
  if required_permission:
    report.add_ok(project)
