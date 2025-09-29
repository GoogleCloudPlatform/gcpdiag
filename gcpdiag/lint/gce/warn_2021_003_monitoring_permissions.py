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
"""GCE VM Instance Access Scope, GCE VM Attached Service Account Permissions \
and APIs Required for Monitoring.

A GCP project should have Cloud Monitoring API enabled.
The service account attached to the GCE VM instances should have the
monitoring.metricWriter IAM role permission.
Also, a GCE instance should have the monitoring.write access scope.
Without these, Ops Agent won't be able to collect metrics from GCE VMs and
display on Metrics Explorer.
"""

import operator as op

from gcpdiag import lint, models
from gcpdiag.queries import apis, crm, gce, iam

ROLE = 'roles/monitoring.metricWriter'
MONITORING_SCOPES = [
    'https://www.googleapis.com/auth/cloud-platform',
    'https://www.googleapis.com/auth/monitoring',
    'https://www.googleapis.com/auth/monitoring.write',
]

ENABLE_MONITORING_API_PROMOT = (
    """Please enable Cloud Monitoring API on the project with the command:\
\ngcloud services enable monitoring.googleapis.com --project=%s\nOps \
Agent requires the API to collect metrics from GCE VMs and display on \
Metrics Explorer""")
VM_NO_MONITORING_SCOPE = """Follow \
https://cloud.google.com/compute/docs/instances/change-service-account\
#changeserviceaccountandscopes\nto enable monitoring.write VM Access Scope."""
SA_NO_METRICS_WRITER = """Follow \
https://cloud.google.com/monitoring/access-control#grant-monitoring-access\n\
to grant roles/monitoring.metricWriter to the VM attached Service Account %s"""
VM_NO_SA = """Follow \
https://cloud.google.com/compute/docs/instances/change-service-account\n\
to attach a Service Account to the VM %s."""


def prefetch_rule(context: models.Context):
  # Make sure that we have the IAM policy in cache.
  project_ids = {i.project_id for i in gce.get_instances(context).values()}
  for pid in project_ids:
    iam.get_project_policy(context.copy_with(project_id=pid))
  crm.get_project(context.project_id)


def run_rule(context: models.Context, report: lint.LintReportRuleInterface):
  if not apis.is_enabled(context.project_id, 'monitoring'):
    report.add_failed(
        crm.get_project(context.project_id),
        ENABLE_MONITORING_API_PROMOT % (context.project_id),
        'Cloud Monitoring API Not Enabled on project %s' % (context.project_id),
    )
    return

  instances = gce.get_instances(context)
  if not instances:
    report.add_skipped(
        None, '', f'No VM instances found in project: {context.project_id}.')
    return

  for i in sorted(instances.values(),
                  key=op.attrgetter('project_id', 'full_path')):
    # GKE nodes are checked by another test.
    if i.is_gke_node():
      continue

    sa = i.service_account
    if not sa:
      report.add_failed(i, VM_NO_SA % (i.name),
                        'VM does not have a Service Account attached')
      continue

    has_scope = set(MONITORING_SCOPES) & set(i.access_scopes)
    if not has_scope:
      report.add_failed(
          i,
          VM_NO_MONITORING_SCOPE,
          'VM does not have monitoring.write Access Scope',
      )
      continue

    iam_policy = iam.get_project_policy(
        context.copy_with(project_id=i.project_id))
    if not iam_policy.has_role_permissions(f'serviceAccount:{sa}', ROLE):
      report.add_failed(
          i,
          SA_NO_METRICS_WRITER % (sa),
          'The attached Service Account of the VM does not have the required'
          ' IAM role: roles/monitoring.metricWriter',
      )
      continue
    report.add_ok(i)
