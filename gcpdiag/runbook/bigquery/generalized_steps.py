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
"""Common steps for BigQuery runbooks."""

import logging
from typing import Dict, Set

from gcpdiag import runbook, utils
from gcpdiag.queries import apis
from gcpdiag.queries import bigquery as bq_queries
from gcpdiag.queries import crm
from gcpdiag.queries.iam import (DEFAULT_SERVICE_ACCOUNT_DOMAINS,
                                 SERVICE_AGENT_DOMAINS)
from gcpdiag.runbook import op
from gcpdiag.runbook.bigquery import flags
from gcpdiag.runbook.bigquery.constants import RUNBOOK_PERMISSION_MAP
from gcpdiag.utils import GcpApiError


class RunPermissionChecks(runbook.Gateway):
  """A comprehensive step to check all mandatory and optional permissions.

  This step is intended to check mandatory and optional permissions for the
  given BigQuery runbook type. It will terminate runbook execution if mandatory
  permissions are missing, or add 'SKIP' notifications for missing optional
  permissions. The step execution will skip altogether if the user is missing
  the resourcemanager.projects.get permission. Finally, it populates the global
  PERMISSION_RESULTS dictionary used throughout the runbook.
  """

  template = 'permissions::mandatory'

  def __init__(self, runbook_id='Failed Query Runbook'):
    super().__init__()
    self.runbook_id = runbook_id
    self.principal_email = ''

  def execute(self):
    """Verifying permissions."""
    if not self.runbook_id:
      raise ValueError('runbook_id must be provided to RunPermissionChecks')
    skip_permission_check = op.get(flags.BQ_SKIP_PERMISSION_CHECK)
    project_placeholder = crm.Project(resource_data={
        'name': 'projects/0000000000',
        'projectId': op.get(flags.PROJECT_ID),
    })
    try:
      self.principal_email = apis.get_user_email()
    except (RuntimeError, AttributeError):
      op.add_skipped(
          project_placeholder,
          reason=
          'Permission check is being skipped because it\'s not possible to successfully identify'
          ' the user executing the investigation.')
      return
    project = project_placeholder
    try:
      project = bq_queries.get_bigquery_project(op.get(flags.PROJECT_ID))
    except utils.GcpApiError as err:
      if 'not found or deleted' in err.message:
        op.add_skipped(
            project_placeholder,
            reason=(f'Project "{project_placeholder.project_id}" not found or'
                    ' deleted. Provide a valid project identifier'),
        )
        self.add_child(bq_queries.BigQueryEnd())
        return
      elif ('Caller does not have required permission to use project'
            in err.message):
        op.add_skipped(
            project_placeholder,
            reason=(
                'You do not have permissions to access project'
                f' "{project_placeholder.project_id}".              \nEnsure'
                f' {self.principal_email} has the "serviceusage.services.use"'
                ' and "serviceusage.services.list" permissions'),
        )
        self.add_child(bq_queries.BigQueryEnd())
        return
    project_id = project.id
    if skip_permission_check:
      necessary_permission_string = ''
      for item in RUNBOOK_PERMISSION_MAP[self.runbook_id]['mandatory_project']:
        necessary_permission_string += (item + ', ')
      op.add_skipped(
          project,
          reason=
          f'Permission check is being skipped because --skip_permission_check=True was used.\
           \nRunbook execution success will depend on the user having the minimal required permissions:\
           \n{necessary_permission_string[:-2]}.\n')
      return
    organization_id = None
    if self.runbook_id != 'Failed Query Runbook':
      try:
        organization = crm.get_organization(op.get(flags.PROJECT_ID))
        if organization:
          organization_id = organization.id
      except GcpApiError as err:
        if 'can\'t access organization for project' in err.message:
          op.info('You don\'t have access to the Organization resource')

    principal = self._get_principal()

    project_policy = bq_queries.get_project_policy(project_id)
    organization_policy = None
    if self.runbook_id != 'Failed Query Runbook':
      if organization_id:
        try:
          organization_policy = bq_queries.get_organization_policy(
              organization_id)
        except GcpApiError as err:
          if 'doesn\'t have access to' in err.message or 'denied on resource' in err.message:
            op.info(
                'User does not have access to the organization policy. Investigation'
                ' completeness and accuracy might depend on the presence of'
                ' organization level permissions.')
          organization_policy = None
    else:
      organization_policy = None

    reqs = RUNBOOK_PERMISSION_MAP.get(self.runbook_id)

    if project_policy is None:
      op.add_skipped(
          resource=project,
          reason=
          f'The permission check step will not be carried out.\nReason: {self.principal_email} '
          'doesn\'t have the resourcemanager.projects.get permission.\nThis is not a blocking '
          'condition - the investigation will continue.\nHowever, successful execution and result '
          'completeness depend on permissions provided.')
    else:
      if reqs:
        mandatory_reqs = reqs.get('mandatory_project', set())
        if mandatory_reqs:
          mandatory_perms = bq_queries.check_permissions_for_principal(
              project_policy, principal, mandatory_reqs)
          missing_mandatory = bq_queries.get_missing_permissions(
              mandatory_reqs, mandatory_perms)

          if missing_mandatory:
            op.add_failed(
                resource=project,
                reason=op.prep_msg(
                    op.FAILURE_REASON,
                    principal=self.principal_email,
                    permissions=', '.join(sorted(missing_mandatory)),
                ),
                remediation=op.prep_msg(op.FAILURE_REMEDIATION,
                                        principal=self.principal_email),
            )

        permission_results: Dict[str, bool] = {}

        optional_project_reqs = reqs.get('optional_project', set())
        if optional_project_reqs:
          project_perms = bq_queries.check_permissions_for_principal(
              project_policy, principal, optional_project_reqs)
          for perm in optional_project_reqs:
            permission_results[perm] = project_perms.get(perm, False)
            if not project_perms.get(perm):
              self._add_info(
                  insight_name=f'Project-level analysis requiring: {perm}',
                  missing_permissions={perm},
                  principal=self.principal_email,
              )

        optional_org_reqs = reqs.get('optional_org', set())
        if organization_id and optional_org_reqs:
          if organization_policy is not None:
            org_perms = bq_queries.check_permissions_for_principal(
                organization_policy, principal, optional_org_reqs)
            for perm in optional_org_reqs:
              permission_results[perm] = org_perms.get(perm, False)
              if not org_perms.get(perm):
                self._add_info(
                    insight_name=
                    f'Organization-level analysis requiring: {perm}',
                    missing_permissions={perm},
                    principal=self.principal_email,
                    is_org=True,
                )
          else:
            op.info(message=(
                f"User {self.principal_email} can't access policies for"
                f' organization {organization_id}.'),)
        op.put(flags.BQ_PERMISSION_RESULTS, permission_results)
        op.add_ok(resource=project,
                  reason='All permission checks are complete.')

  def _get_principal(self):
    principal_email_doman = self.principal_email.partition('@')[2]
    if (principal_email_doman in SERVICE_AGENT_DOMAINS or
        principal_email_doman.startswith('gcp-sa-') or
        self.principal_email.endswith(DEFAULT_SERVICE_ACCOUNT_DOMAINS[1])):
      principal_type = 'service_account'
    else:
      principal_type = 'user'

    return principal_type + ':' + self.principal_email

  def _add_info(
      self,
      insight_name: str,
      missing_permissions: Set[str],
      principal: str,
      is_org: bool = False,
  ):
    """Helper to generate a consistent 'skipped' message for optional permissions."""

    permissions = ', '.join(sorted(missing_permissions))
    logging.debug('permissions = %s', permissions)
    level = 'organization' if is_org else 'project'

    message = f'A sub-analysis was skipped: {insight_name}.'
    message += f'\n\tTo enable this analysis, grant the principal {principal}'
    message += (f' the IAM permission at the {level} level')

    op.info(message=message)
