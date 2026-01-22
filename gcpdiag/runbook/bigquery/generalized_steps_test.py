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
"""Tests for generalized steps in BigQuery runbooks."""

import datetime
import unittest
from unittest import mock

from gcpdiag import models, utils
from gcpdiag.queries import apis_stub, crm
from gcpdiag.runbook import op
from gcpdiag.runbook.bigquery import flags, generalized_steps

DUMMY_PROJECT_ID = 'gcpdiag-bigquery1-aaaa'


class MockMessage:
  """Mock messages for testing."""

  def get_msg(self, key, **kwargs):
    del kwargs
    return f'{key}'


class RunPermissionChecksTest(unittest.TestCase):
  """Test cases for RunPermissionChecks."""

  def setUp(self):
    super().setUp()
    self.enterContext(
        mock.patch('gcpdiag.queries.apis.get_api', new=apis_stub.get_api_stub))
    self.mock_get_user_email = self.enterContext(
        mock.patch('gcpdiag.queries.apis.get_user_email'))
    self.mock_get_bigquery_project = self.enterContext(
        mock.patch('gcpdiag.queries.bigquery.get_bigquery_project'))
    self.mock_crm_get_organization = self.enterContext(
        mock.patch('gcpdiag.queries.crm.get_organization'))
    self.mock_bq_get_project_policy = self.enterContext(
        mock.patch('gcpdiag.queries.bigquery.get_project_policy'))
    self.mock_bq_get_organization_policy = self.enterContext(
        mock.patch('gcpdiag.queries.bigquery.get_organization_policy'))
    self.mock_runbook_permission_map = self.enterContext(
        mock.patch.dict(
            generalized_steps.RUNBOOK_PERMISSION_MAP,
            {
                'Failed Query Runbook': {
                    'mandatory_project': {'p1'},
                    'optional_project': set(),
                    'optional_org': set(),
                },
                'other-runbook': {
                    'mandatory_project': {'p1'},
                    'optional_project': {'p2'},
                    'optional_org': {'o1'},
                },
            },
        ))

    self.mock_interface = mock.create_autospec(op.InteractionInterface,
                                               instance=True)
    self.mock_interface.rm = mock.Mock()
    self.operator = op.Operator(self.mock_interface)
    self.operator.run_id = 'test-run'
    self.operator.messages = MockMessage()
    self.operator.context = models.Context(project_id=DUMMY_PROJECT_ID)

    self.params = {
        flags.PROJECT_ID: DUMMY_PROJECT_ID,
        flags.BQ_SKIP_PERMISSION_CHECK: False,
        'start_time': datetime.datetime.now(),
        'end_time': datetime.datetime.now(),
    }
    self.operator.parameters = self.params

    self.mock_project = mock.Mock(spec=crm.Project)
    self.mock_project.id = DUMMY_PROJECT_ID
    self.mock_project.name = f'projects/{self.mock_project.id}'
    self.mock_get_bigquery_project.return_value = self.mock_project
    self.mock_get_user_email.return_value = 'test@example.com'
    self.mock_project_policy = mock.MagicMock()
    self.mock_project_policy.has_permission.return_value = True
    self.mock_bq_get_project_policy.return_value = self.mock_project_policy
    self.mock_org_policy = mock.MagicMock()
    self.mock_org_policy.has_permission.return_value = True
    self.mock_bq_get_organization_policy.return_value = self.mock_org_policy

  def test_no_runbook_id_raises_value_error(self):
    with self.assertRaises(ValueError):
      step = generalized_steps.RunPermissionChecks(runbook_id=None)
      with op.operator_context(self.operator):
        self.operator.set_step(step)
        step.execute()

  def test_skip_permission_check_true(self):
    self.params[flags.BQ_SKIP_PERMISSION_CHECK] = True
    step = generalized_steps.RunPermissionChecks()
    with op.operator_context(self.operator):
      self.operator.set_step(step)
      step.execute()
    self.mock_interface.add_skipped.assert_called_once()
    self.assertIn(
        'Permission check is being skipped',
        self.mock_interface.add_skipped.call_args[1]['reason'],
    )

  def test_get_user_email_fails(self):
    self.mock_get_user_email.side_effect = RuntimeError('Can not get email')
    step = generalized_steps.RunPermissionChecks()
    with op.operator_context(self.operator):
      self.operator.set_step(step)
      step.execute()
    self.mock_interface.add_skipped.assert_called_once()
    self.assertIn(
        "it's not possible to successfully identify the user",
        self.mock_interface.add_skipped.call_args[1]['reason'],
    )

  def test_get_project_policy_is_none(self):
    self.mock_bq_get_project_policy.return_value = None
    step = generalized_steps.RunPermissionChecks()
    with op.operator_context(self.operator):
      self.operator.set_step(step)
      step.execute()
    self.mock_interface.add_skipped.assert_called_once()
    self.assertIn(
        "doesn't have the resourcemanager.projects.get permission",
        self.mock_interface.add_skipped.call_args[1]['reason'],
    )

  def test_missing_mandatory_permissions(self):
    self.mock_project_policy.has_permission.return_value = False
    step = generalized_steps.RunPermissionChecks()
    with op.operator_context(self.operator):
      self.operator.set_step(step)
      step.execute()
    self.mock_interface.add_failed.assert_called_once()

  def test_missing_optional_project_permissions(self):
    generalized_steps.RUNBOOK_PERMISSION_MAP['Failed Query Runbook'] = {
        'mandatory_project': {'p1'},
        'optional_project': {'p2'},
        'optional_org': set(),
    }
    self.mock_project_policy.has_permission.side_effect = lambda p, perm: perm == 'p1'
    step = generalized_steps.RunPermissionChecks()
    with op.operator_context(self.operator):
      self.operator.set_step(step)
      step.execute()
    self.mock_interface.info.assert_called_with(
        'A sub-analysis was skipped: Project-level analysis requiring:'
        ' p2.\n\tTo enable this analysis, grant the principal'
        ' test@example.com the IAM permission at the project level',
        'INFO',
    )
    self.mock_interface.add_ok.assert_called_once()

  def test_runbook_id_not_failed_query_missing_org_perm(self):
    self.mock_crm_get_organization.return_value = mock.Mock(id='org1')
    self.mock_org_policy.has_permission.return_value = False
    step = generalized_steps.RunPermissionChecks(runbook_id='other-runbook')
    with op.operator_context(self.operator):
      self.operator.set_step(step)
      step.execute()
    self.mock_interface.info.assert_called_with(
        'A sub-analysis was skipped: Organization-level analysis requiring:'
        ' o1.\n\tTo enable this analysis, grant the principal'
        ' test@example.com the IAM permission at the organization level',
        'INFO',
    )
    self.mock_interface.add_ok.assert_called_once()

  def test_get_org_fails(self):
    self.mock_crm_get_organization.side_effect = utils.GcpApiError(
        Exception("can't access organization for project"))
    step = generalized_steps.RunPermissionChecks(runbook_id='other-runbook')
    with op.operator_context(self.operator):
      self.operator.set_step(step)
      step.execute()
    self.mock_interface.info.assert_any_call(
        "You don't have access to the Organization resource", 'INFO')
    self.mock_interface.add_ok.assert_called_once()

  def test_get_org_policy_fails(self):
    self.mock_crm_get_organization.return_value = mock.Mock(id='org1')
    self.mock_bq_get_organization_policy.side_effect = utils.GcpApiError(
        Exception('denied on resource'))
    step = generalized_steps.RunPermissionChecks(runbook_id='other-runbook')
    with op.operator_context(self.operator):
      self.operator.set_step(step)
      step.execute()
    self.mock_interface.info.assert_has_calls([
        mock.call(
            'User does not have access to the organization policy.'
            ' Investigation completeness and accuracy might depend on the'
            ' presence of organization level permissions.',
            'INFO',
        ),
        mock.call(
            "User test@example.com can't access policies for organization"
            ' org1.',
            'INFO',
        ),
    ])
    self.mock_interface.add_ok.assert_called_once()

  def test_service_account_principal_gcp_sa(self):
    self.mock_get_user_email.return_value = (
        'test@gcp-sa-project.iam.gserviceaccount.com')
    step = generalized_steps.RunPermissionChecks()
    with op.operator_context(self.operator):
      self.operator.set_step(step)
      step.execute()
    self.mock_project_policy.has_permission.assert_called_with(
        'service_account:test@gcp-sa-project.iam.gserviceaccount.com',
        'p1',
    )
    self.mock_interface.add_ok.assert_called_once()

  def test_service_account_principal_default(self):
    self.mock_get_user_email.return_value = 'test@developer.gserviceaccount.com'
    step = generalized_steps.RunPermissionChecks()
    with op.operator_context(self.operator):
      self.operator.set_step(step)
      step.execute()
    self.mock_project_policy.has_permission.assert_called_with(
        'service_account:test@developer.gserviceaccount.com',
        'p1',
    )
    self.mock_interface.add_ok.assert_called_once()
