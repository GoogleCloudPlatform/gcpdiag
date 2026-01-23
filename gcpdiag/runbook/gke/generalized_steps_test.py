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
"""Tests for gke/generalized_steps.py."""

import unittest
from unittest import mock

from gcpdiag.queries import apis_stub
from gcpdiag.runbook import op
from gcpdiag.runbook.gke import flags, generalized_steps


class MockMessage:
  """Mock messages for testing."""

  def get_msg(self, key, **kwargs):
    del kwargs
    return f'{key}'


class GkeStepTestBase(unittest.TestCase):
  """Base class for GKE generalized step tests."""

  def setUp(self):
    super().setUp()
    self.enterContext(
        mock.patch('gcpdiag.queries.apis.get_api', new=apis_stub.get_api_stub))
    self.mock_get_user_email = self.enterContext(
        mock.patch('gcpdiag.queries.apis.get_user_email'))
    self.mock_is_enabled = self.enterContext(
        mock.patch('gcpdiag.queries.apis.is_enabled'))
    self.mock_is_enabled.return_value = True
    self.mock_get_user_email.return_value = 'test@example.com'

    self.mock_interface = mock.create_autospec(op.InteractionInterface,
                                               instance=True)
    self.mock_interface.rm = mock.Mock()
    self.operator = op.Operator(self.mock_interface)
    self.operator.run_id = 'test-run'
    self.operator.messages = MockMessage()
    self.mock_op_get = self.enterContext(mock.patch('gcpdiag.runbook.op.get'))
    self.mock_op_add_ok = self.enterContext(
        mock.patch('gcpdiag.runbook.op.add_ok'))
    self.mock_op_add_failed = self.enterContext(
        mock.patch('gcpdiag.runbook.op.add_failed'))
    self.mock_op_get_context = self.enterContext(
        mock.patch('gcpdiag.runbook.op.get_context'))

    self.params = {
        flags.PROJECT_ID: 'test-project',
        flags.LOCATION: 'us-central1',
        flags.GKE_CLUSTER_NAME: 'test-cluster',
    }
    self.mock_op_get.side_effect = lambda key, default=None: self.params.get(
        key, default)


class ApiEnabledTest(GkeStepTestBase):
  """Test ApiEnabled step."""

  @mock.patch('gcpdiag.queries.apis.is_enabled')
  @mock.patch('gcpdiag.queries.crm.get_project')
  def test_api_enabled_ok(self, unused_mock_get_project, mock_is_enabled):
    mock_is_enabled.return_value = True
    step = generalized_steps.ApiEnabled()
    step.api_name = 'container.googleapis.com'
    step.execute()
    self.mock_op_add_ok.assert_called_once()

  @mock.patch('gcpdiag.queries.apis.is_enabled')
  @mock.patch('gcpdiag.queries.crm.get_project')
  def test_api_enabled_failed(self, unused_mock_get_project, mock_is_enabled):
    mock_is_enabled.return_value = False
    step = generalized_steps.ApiEnabled()
    step.api_name = 'container.googleapis.com'
    step.execute()
    self.mock_op_add_failed.assert_called_once()


class NodePoolScopeTest(GkeStepTestBase):
  """Test NodePoolScope step."""

  @mock.patch('gcpdiag.queries.gke.get_clusters')
  @mock.patch('gcpdiag.lint.gke.util.get_cluster_object')
  def test_nodepool_scope_ok(self, mock_get_cluster_obj,
                             unused_mock_get_clusters):
    mock_nodepool = mock.Mock()
    mock_nodepool.config.oauth_scopes = [
        'https://www.googleapis.com/auth/cloud-platform'
    ]
    mock_cluster = mock.Mock()
    mock_cluster.nodepools = [mock_nodepool]
    mock_get_cluster_obj.return_value = mock_cluster

    step = generalized_steps.NodePoolScope()
    step.required_scopes = ['https://www.googleapis.com/auth/cloud-platform']
    step.service_name = 'Cloud Platform'
    step.execute()
    self.mock_op_add_ok.assert_called_once()

  @mock.patch('gcpdiag.queries.gke.get_clusters')
  @mock.patch('gcpdiag.lint.gke.util.get_cluster_object')
  def test_nodepool_scope_failed(self, mock_get_cluster_obj,
                                 unused_mock_get_clusters):
    mock_nodepool = mock.Mock()
    mock_nodepool.config.oauth_scopes = ['wrong-scope']
    mock_cluster = mock.Mock()
    mock_cluster.nodepools = [mock_nodepool]
    mock_get_cluster_obj.return_value = mock_cluster

    step = generalized_steps.NodePoolScope()
    step.required_scopes = ['correct-scope']
    step.service_name = 'Cloud Platform'
    step.execute()
    self.mock_op_add_failed.assert_called_once()


class ServiceAccountPermissionTest(GkeStepTestBase):
  """Test ServiceAccountPermission step."""

  @mock.patch('gcpdiag.queries.gke.get_clusters')
  @mock.patch('gcpdiag.lint.gke.util.get_cluster_object')
  @mock.patch('gcpdiag.queries.iam.get_project_policy')
  @mock.patch('gcpdiag.queries.iam.is_service_account_enabled')
  def test_sa_permission_ok(self, mock_sa_enabled, mock_get_policy,
                            mock_get_cluster_obj, unused_mock_get_clusters):
    mock_sa_enabled.return_value = True
    mock_policy = mock.Mock()
    mock_policy.has_role_permissions.return_value = True
    mock_get_policy.return_value = mock_policy

    mock_nodepool = mock.Mock()
    mock_nodepool.service_account = 'test-sa@project.iam.gserviceaccount.com'
    mock_cluster = mock.Mock()
    mock_cluster.nodepools = [mock_nodepool]
    mock_get_cluster_obj.return_value = mock_cluster

    step = generalized_steps.ServiceAccountPermission()
    step.required_roles = ['roles/container.nodeServiceAccount']
    step.service_name = 'GKE'
    step.execute()
    self.mock_op_add_ok.assert_called_once()

  @mock.patch('gcpdiag.queries.gke.get_clusters')
  @mock.patch('gcpdiag.lint.gke.util.get_cluster_object')
  @mock.patch('gcpdiag.queries.iam.get_project_policy')
  @mock.patch('gcpdiag.queries.iam.is_service_account_enabled')
  def test_sa_disabled(self, mock_sa_enabled, unused_mock_get_policy,
                       mock_get_cluster_obj, unused_mock_get_clusters):
    mock_sa_enabled.return_value = False
    mock_nodepool = mock.Mock()
    mock_cluster = mock.Mock()
    mock_cluster.nodepools = [mock_nodepool]
    mock_get_cluster_obj.return_value = mock_cluster

    step = generalized_steps.ServiceAccountPermission()
    step.required_roles = ['roles/container.nodeServiceAccount']
    step.service_name = 'GKE'
    step.execute()
    # Should fail because SA is disabled
    self.mock_op_add_failed.assert_called()
