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
"""Dataproc VM Service Account has necessary permissions

VM Service Account should have required permissions to function correctly.
Though required permission may be granted via user-managed role or primitive
roles, it is recommended to grant roles/dataproc.worker on project level.
"""

from gcpdiag import lint, models
from gcpdiag.queries import dataproc, iam

WORKER_ROLE = 'roles/dataproc.worker'

clusters_by_project = {}
policies_by_project = {}


def prefetch_rule(context: models.Context):
  clusters_by_project[context.project_id] = dataproc.get_clusters(context)
  policies_by_project[context.project_id] = iam.get_project_policy(context)


def run_rule(context: models.Context,
             report: lint.LintReportRuleInterface) -> None:

  clusters = clusters_by_project[context.project_id]
  if not clusters:
    report.add_skipped(None, 'no dataproc clusters found')

  for cluster in clusters:
    sa_email = cluster.vm_service_account_email
    sa_exists = iam.is_service_account_existing(email=sa_email, context=context)
    if not sa_exists:
      # Non-existent SA is also a non-normal situation, however our intent was to
      # have a separate rule for that, so that one rule has more-or-less one
      # reason to fail
      report.add_skipped(
          cluster,
          'VM Service Account associated with Dataproc cluster was not found')
      continue

    sa_has_role = policies_by_project[context.project_id].has_role_permissions(
        member=f'serviceAccount:{sa_email}', role=WORKER_ROLE)

    if sa_has_role:
      report.add_ok(cluster)
    else:
      report.add_failed(
          cluster,
          f'Service account {sa_email} does not have enough permissions')
