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
"""Test class for gke/Image_pull."""

import unittest
from unittest import mock

from gcpdiag import config
from gcpdiag.queries import apis_stub
from gcpdiag.runbook import gke, op, snapshot_test_base
from gcpdiag.runbook.gke import flags, image_pull
from gcpdiag.utils import GcpApiError


class MockMessage:
  """Mock messages for testing."""

  def get_msg(self, key, **kwargs):
    del kwargs
    return f'{key}'


class Test(snapshot_test_base.RulesSnapshotTestBase):
  rule_pkg = gke
  runbook_name = 'gke/image-pull'
  config.init({'auto': True, 'interface': 'cli'})

  rule_parameters = [{
      'project_id': 'gcpdiag-gke-cluster-autoscaler-rrrr',
      'gke_cluster_name': 'gke-cluster',
      'location': 'europe-west10',
      'start_time': '2024-08-12T01:00:00Z',
      'end_time': '2024-08-12T23:00:00Z'
  }]


class TestImagePull(unittest.TestCase):
  """Unit tests for GKE Image Pull runbook."""

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
    self.project_id = 'test-project'
    self.cluster_name = 'test-cluster'
    self.location = 'us-central1'
    self.enterContext(
        mock.patch('gcpdiag.runbook.op.get_context', autospec=True))
    self.enterContext(
        mock.patch(
            'gcpdiag.runbook.op.prep_msg',
            side_effect=lambda x, **y: x,
            autospec=True,
        ))

  @mock.patch('gcpdiag.runbook.gke.image_pull.op.get')
  @mock.patch('gcpdiag.queries.apis.is_enabled')
  @mock.patch('gcpdiag.queries.crm.get_project')
  @mock.patch('gcpdiag.runbook.gke.image_pull.op.add_skipped')
  def test_image_pull_start_skips_when_logging_disabled(self, mock_add_skipped,
                                                        mock_get_project,
                                                        mock_is_enabled,
                                                        mock_op_get):
    """ImagePullStart should skip execution if the Logging API is disabled."""
    del mock_get_project
    mock_op_get.side_effect = (lambda key: self.project_id
                               if key == flags.PROJECT_ID else None)
    mock_is_enabled.return_value = False
    step = image_pull.ImagePullStart()

    step.execute()

    mock_add_skipped.assert_called_once()
    self.assertIn('Logging disabled', mock_add_skipped.call_args[1]['reason'])

  @mock.patch('gcpdiag.queries.apis.is_enabled')
  @mock.patch('gcpdiag.runbook.gke.image_pull.crm.get_project')
  @mock.patch('gcpdiag.runbook.gke.image_pull.op.get')
  @mock.patch('gcpdiag.queries.gke.get_cluster')
  @mock.patch('gcpdiag.runbook.gke.image_pull.op.add_skipped')
  def test_image_pull_start_skips_when_cluster_not_found(
      self,
      mock_add_skipped,
      mock_get_cluster,
      mock_op_get,
      mock_get_project,
      mock_is_enabled,
  ):
    """ImagePullStart should skip execution if the cluster does not exist."""
    del mock_get_project
    mock_is_enabled.return_value = True
    mock_op_get.side_effect = {
        flags.PROJECT_ID: self.project_id,
        flags.GKE_CLUSTER_NAME: self.cluster_name,
        flags.LOCATION: self.location,
    }.get
    mock_response = mock.Mock()
    mock_response.status = 404
    mock_response.content = b'{"error": "cluster not found"}'
    mock_get_cluster.side_effect = GcpApiError(mock_response)
    step = image_pull.ImagePullStart()

    step.execute()

    mock_add_skipped.assert_called_once()
    self.assertIn('does not exist', mock_add_skipped.call_args[1]['reason'])

  @mock.patch('gcpdiag.runbook.gke.image_pull.local_realtime_query')
  @mock.patch('gcpdiag.runbook.gke.image_pull.op.add_failed')
  @mock.patch('gcpdiag.runbook.gke.image_pull.crm.get_project')
  @mock.patch('gcpdiag.runbook.gke.image_pull.op.get')
  def test_image_not_found_fails_when_logs_detected(self, mock_op_get,
                                                    mock_get_project,
                                                    mock_add_failed,
                                                    mock_query):
    """ImageNotFound should report failure when 'not found' logs are present."""
    del mock_get_project
    mock_op_get.return_value = 'test'
    mock_query.return_value = [{
        'resource': {
            'labels': {
                'pod_name': 'test-pod'
            }
        },
        'jsonPayload': {
            'message': 'Failed to pull image: not found'
        },
    }]
    step = image_pull.ImageNotFound()
    step.execute()
    mock_add_failed.assert_called_once()

  def test_format_log_entries_handles_missing_labels(self):
    """format_log_entries should provide 'Not found' placeholders when labels are missing."""
    log_entries = [{'jsonPayload': {'message': 'error'}}]

    result = image_pull.format_log_entries(log_entries)

    self.assertIn('Cluster name: Not found', result)
    self.assertIn('Log Message: error', result)

  def test_legacy_parameter_handler_migrates_name_to_gke_cluster_name(self):
    """legacy_parameter_handler should migrate the deprecated 'name' flag."""
    params = {flags.NAME: 'old-name'}
    runbook_obj = image_pull.ImagePull()

    runbook_obj.legacy_parameter_handler(params)

    self.assertEqual(params[flags.GKE_CLUSTER_NAME], 'old-name')
    self.assertNotIn(flags.NAME, params)

  @mock.patch('gcpdiag.runbook.gke.image_pull.op.prompt')
  @mock.patch('gcpdiag.runbook.gke.image_pull.op.info')
  def test_image_pull_end_shows_info_on_no_response(self, mock_op_info,
                                                    mock_op_prompt):
    """ImagePullEnd should show an end message if user is not satisfied."""

    mock_op_prompt.return_value = op.NO
    step = image_pull.ImagePullEnd()

    step.execute()

    mock_op_info.assert_called_once()


class TestImagePullCoverage(unittest.TestCase):
  """Additional unit tests to achieve 100% coverage for image_pull.py."""

  def setUp(self):
    super().setUp()
    self.project_id = 'test-project'
    self.cluster_name = 'test-cluster'
    self.location = 'us-central1'
    self.enterContext(
        mock.patch('gcpdiag.runbook.op.get_context', autospec=True))
    self.enterContext(
        mock.patch(
            'gcpdiag.runbook.op.prep_msg',
            side_effect=lambda x, **y: x,
            autospec=True,
        ))

  @mock.patch('gcpdiag.queries.logs.realtime_query')
  @mock.patch('gcpdiag.runbook.gke.image_pull.op.get')
  def test_local_realtime_query_correctly_calls_logs_query(
      self, mock_op_get, mock_logs_query):
    """local_realtime_query should use parameters from op.get for the logs query."""
    mock_op_get.side_effect = {
        flags.PROJECT_ID: self.project_id,
        flags.START_TIME: '2024-01-01T00:00:00Z',
        flags.END_TIME: '2024-01-01T01:00:00Z',
    }.get
    filters = ['filter1', 'filter2']

    image_pull.local_realtime_query(filters)

    mock_logs_query.assert_called_once_with(project_id=self.project_id,
                                            start_time='2024-01-01T00:00:00Z',
                                            end_time='2024-01-01T01:00:00Z',
                                            filter_str='filter1\nfilter2')

  @mock.patch('gcpdiag.runbook.DiagnosticTree.add_end')
  @mock.patch('gcpdiag.runbook.DiagnosticTree.add_step')
  @mock.patch('gcpdiag.runbook.DiagnosticTree.add_start')
  def test_build_tree_constructs_correct_diagnostic_structure(
      self, mock_add_start, mock_add_step, mock_add_end):
    """build_tree should define the expected sequence of diagnostic steps."""

    dtree = image_pull.ImagePull()

    dtree.build_tree()

    mock_add_start.assert_called_once()
    mock_add_end.assert_called_once()
    self.assertGreater(mock_add_step.call_count, 1)

  @mock.patch('gcpdiag.runbook.gke.image_pull.local_realtime_query')
  @mock.patch('gcpdiag.runbook.gke.image_pull.op.add_ok')
  @mock.patch('gcpdiag.runbook.gke.image_pull.crm.get_project')
  @mock.patch('gcpdiag.runbook.gke.image_pull.op.get')
  def test_diagnostic_steps_report_ok_when_no_logs_found(
      self, mock_op_get, mock_get_project, mock_add_ok, mock_query):
    """Verify Success paths for diagnostic steps (e.g., ImageForbidden, ImageDnsIssue)."""
    del mock_get_project
    mock_op_get.return_value = 'test'
    mock_query.return_value = []
    steps_to_test = [
        image_pull.ImageNotFound(),
        image_pull.ImageForbidden(),
        image_pull.ImageDnsIssue(),
        image_pull.ImageConnectionTimeout(),
        image_pull.ImageNotFoundInsufficientScope()
    ]

    for step in steps_to_test:
      step.execute()
      mock_add_ok.assert_called()
      mock_add_ok.reset_mock()

  @mock.patch('gcpdiag.runbook.gke.image_pull.local_realtime_query')
  @mock.patch('gcpdiag.runbook.gke.image_pull.op.add_failed')
  @mock.patch('gcpdiag.runbook.gke.image_pull.crm.get_project')
  @mock.patch('gcpdiag.runbook.gke.image_pull.op.get')
  def test_steps_fail_on_matching_log_entries(self, mock_op_get,
                                              mock_get_project, mock_add_failed,
                                              mock_query):
    """Verify Failure paths for specific error classes like Forbidden or DNS issues."""
    del mock_get_project
    mock_op_get.return_value = 'test'
    mock_query.return_value = [{
        'jsonPayload': {
            'message': 'error message'
        },
        'resource': {}
    }]
    steps = [
        image_pull.ImageForbidden(),
        image_pull.ImageDnsIssue(),
        image_pull.ImageConnectionTimeoutRestrictedPrivate(),
        image_pull.ImageConnectionTimeout(),
        image_pull.ImageNotFoundInsufficientScope()
    ]
    for step in steps:
      step.execute()
      mock_add_failed.assert_called()
      mock_add_failed.reset_mock()

  @mock.patch('gcpdiag.runbook.gke.image_pull.op.get')
  @mock.patch('gcpdiag.queries.apis.is_enabled')
  @mock.patch('gcpdiag.queries.gke.get_cluster')
  @mock.patch('gcpdiag.queries.crm.get_project')
  @mock.patch('gcpdiag.runbook.gke.image_pull.op.add_ok')
  def test_image_pull_start_succeeds_when_cluster_and_logging_active(
      self,
      mock_add_ok,
      mock_get_project,
      mock_get_cluster,
      mock_is_enabled,
      mock_op_get,
  ):
    """ImagePullStart should report OK when requirements are met."""
    del mock_get_project
    mock_op_get.return_value = 'test'
    mock_is_enabled.return_value = True
    mock_cluster = mock.Mock()
    mock_cluster.name = 'test-cluster'
    mock_cluster.name = 'test-cluster'
    mock_get_cluster.return_value = mock_cluster

    step = image_pull.ImagePullStart()
    step.execute()
    mock_add_ok.assert_called_once()
    self.assertIn('found', mock_add_ok.call_args[1]['reason'])
