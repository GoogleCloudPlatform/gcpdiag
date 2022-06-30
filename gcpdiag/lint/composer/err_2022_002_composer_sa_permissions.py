# Copyright 2022 Google LLC
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
"""Composer Environment Service Account permissions

Verify that the Composer Environment Service Account exists and has
the Composer Worker role on the project.
"""

from gcpdiag import lint, models
from gcpdiag.queries import composer, iam

# `composer.worker` role has broader permissions than `editor`, but any of them
# is sufficient to run a composer environment
ROLE = 'roles/composer.worker'
ALT_ROLES = ['roles/editor']

# `iam.serviceAccountUser` is only required for private IP environments
PRIVATE_IP_ROLE = 'roles/iam.serviceAccountUser'

environments_by_project = {}

policy_by_project = {}
policy_by_service_account = {}


def prefetch_rule(context: models.Context):
  environments_by_project[context.project_id] = composer.get_environments(
      context)

  policy_by_project[context.project_id] = iam.get_project_policy(
      context.project_id)
  for environment in environments_by_project[context.project_id]:
    # Service account policy is needed for private IP envs only
    if not environment.is_private_ip():
      continue

    if environment.service_account in policy_by_service_account:
      continue

    policy_by_service_account[
        environment.service_account] = iam.get_service_account_iam_policy(
            context.project_id, environment.service_account)


def run_rule(context: models.Context,
             report: lint.LintReportRuleInterface) -> None:
  environments = environments_by_project[context.project_id]
  if len(environments) == 0:
    report.add_skipped(None, 'no composer environments found')
    return

  for environment in environments:
    has_failed = False
    service_account = environment.service_account

    project_policy = policy_by_project[environment.project_id]
    for role in [ROLE] + ALT_ROLES:
      if project_policy.has_role_permissions(
          f'serviceAccount:{service_account}', role):
        break
    else:
      has_failed = True
      # `composer.worker` is preferred, using it in error messages
      report.add_failed(environment, (f'service account: {service_account}\n'
                                      f'missing role: {ROLE}'))

    if environment.is_private_ip():
      service_account_policy = policy_by_service_account[
          environment.service_account]
      for scope in (service_account_policy, project_policy):
        if scope.has_role_permissions(f'serviceAccount:{service_account}',
                                      PRIVATE_IP_ROLE):
          break
      else:
        has_failed = True
        report.add_failed(environment, (f'service account: {service_account}\n'
                                        f'missing role: {PRIVATE_IP_ROLE}'))

    if not has_failed:
      report.add_ok(environment)
