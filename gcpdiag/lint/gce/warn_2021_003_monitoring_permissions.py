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
"""GCE instance service account permissions for monitoring.

The service account used by GCE instance should have the monitoring.metricWriter
permission and a GCE instance should have the monitoring.write access scope,
otherwise, if you install the ops or monitoring agent, it won't be able to send
the metrics to Cloud Monitoring.
"""

import operator as op

from gcpdiag import lint, models
from gcpdiag.queries import gce, iam

ROLE = 'roles/monitoring.metricWriter'
MONITORING_SCOPES = [
    'https://www.googleapis.com/auth/cloud-platform',
    'https://www.googleapis.com/auth/monitoring',
    'https://www.googleapis.com/auth/monitoring.write'
]


def prefetch_rule(context: models.Context):
  # Make sure that we have the IAM policy in cache.
  iam.get_project_policy(context.project_id)


def run_rule(context: models.Context, report: lint.LintReportRuleInterface):
  instances = gce.get_instances(context)
  instances_count = 0
  for i in sorted(instances.values(), key=op.attrgetter('project_id', 'name')):
    # GKE nodes are checked by another test.
    if i.is_gke_node():
      continue
    message = []
    instances_count += 1
    iam_policy = iam.get_project_policy(i.project_id)
    sa = i.service_account
    has_scope = set(MONITORING_SCOPES) & set(i.access_scopes)

    if not has_scope:
      message.append('missing scope: monitoring.write')

    if not sa:
      message.append('no service account')
    elif not iam_policy.has_role_permissions(f'serviceAccount:{sa}', ROLE):
      message.append(f'service account: {sa}\nmissing role: {ROLE}')

    if message:
      report.add_failed(i, '\n'.join(message))
    else:
      report.add_ok(i)

  if not instances_count:
    report.add_skipped(None, 'no instances found')
