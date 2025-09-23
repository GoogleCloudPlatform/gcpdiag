# Copyright 2021 Google LLC
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
"""Compute Engine VM has the proper scope to connect using the Cloud SQL Admin API

The service account used by Compute Engine VM should have permission
(roles/cloudsql.client) to connect to the Cloud SQL using the Cloud SQL Admin
API, otherwise connection won't work.
"""

import operator as op

from gcpdiag import lint, models
from gcpdiag.lint.gce import utils
from gcpdiag.queries import apis, gce, iam, network

ROLE = 'roles/cloudsql.client'
CLOUDSQL_ADMIN_SCOPES = [
    'https://www.googleapis.com/auth/cloud-platform',
    'https://www.googleapis.com/auth/sqlservice.admin'
]


def run_rule(context: models.Context, report: lint.LintReportRuleInterface):
  if not apis.is_enabled(context.project_id, 'compute'):
    report.add_skipped(None, 'compute API is disabled')
    return

  instances = gce.get_instances(context)

  if not instances:
    report.add_skipped(None, 'no instances found')
    return

  cloudsql_peered_networks = {}

  for vpc in network.get_networks(context):
    if any(utils.is_cloudsql_peer_network(peer.url) for peer in vpc.peerings):
      cloudsql_peered_networks[vpc.self_link] = vpc

  if not cloudsql_peered_networks:
    report.add_skipped(None, 'no Cloud SQL peered vpc found')
    return

  for instance in sorted(instances.values(),
                         key=op.attrgetter('project_id', 'name')):
    if instance.network.self_link not in cloudsql_peered_networks:
      continue

    iam_policy = iam.get_project_policy(instance.project_id)
    service_account = instance.service_account
    has_scope = set(CLOUDSQL_ADMIN_SCOPES) & set(instance.access_scopes)

    message = []

    if not has_scope:
      message.append('missing scope: sqlservice.admin')

    if not service_account:
      message.append('no service account')
    elif not iam_policy.has_role_permissions(
        f'serviceAccount:{service_account}', ROLE):
      message.append(
          f'service_account: {service_account}\nmissing role: {ROLE}')

    if message:
      report.add_failed(instance, '\n'.join(message))
    else:
      report.add_ok(instance)
