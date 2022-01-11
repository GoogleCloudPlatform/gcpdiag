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
"""OS Config service account has the required permissions.

The OS Config service account (@gcp-sa-osconfig.iam.gserviceaccount.com) must
have the osconfig.serviceAgent role.
"""
import operator

from gcpdiag import lint, models
from gcpdiag.queries import crm, gce, iam

ROLE = 'roles/osconfig.serviceAgent'


#check metadata on project first if not per instance and skip get_metadata
def prefetch_rule(context: models.Context):
  # Make sure that we have the IAM policy in cache.
  project_ids = {i.project_id for i in gce.get_instances(context).values()}
  for pid in project_ids:
    iam.get_project_policy(pid)


def run_rule(context: models.Context, report: lint.LintReportRuleInterface):
  instances = gce.get_instances(context)
  instances_count = 0
  for i in sorted(instances.values(),
                  key=operator.attrgetter('project_id', 'name')):
    # GKE nodes never have OS Config enabled
    if i.is_gke_node():
      continue
    if i.get_metadata('enable-osconfig'):
      osconfig_service_account = 'service-{}@gcp-sa-osconfig.iam.gserviceaccount.com'.format(
          crm.get_project(i.project_id).number)
      instances_count += 1
      iam_policy = iam.get_project_policy(i.project_id)
      sa = i.service_account
      if not sa:
        # if an SA is not attched to the vm check if the service agent has the correct role
        if not iam_policy.has_role_permissions(
            f'serviceAccount:{osconfig_service_account}', ROLE):
          report.add_failed(
              i,
              f'service account: {osconfig_service_account}\nmissing role: {ROLE}'
          )
        else:
          report.add_ok(i)
      else:
        report.add_ok(i)
  if not instances_count:
    report.add_skipped(None, 'no instances found with OS Config enabled')
