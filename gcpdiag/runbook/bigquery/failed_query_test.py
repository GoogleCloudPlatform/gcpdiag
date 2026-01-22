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
"""Test class for the bigquery/failed-query runbook."""

import datetime
import unittest
from unittest import mock

from gcpdiag import config, models, utils
from gcpdiag.queries import apis_stub
from gcpdiag.runbook import bigquery, op, snapshot_test_base
from gcpdiag.runbook.bigquery import failed_query, flags


class Test(snapshot_test_base.RulesSnapshotTestBase):
  """Test cases for the BigQuery Failed Query runbook."""

  rule_pkg = bigquery
  runbook_name = 'bigquery/failed-query'
  runbook_id = 'Failed Query Runbook'
  config.init({'auto': True, 'interface': 'cli'})
  rule_parameters = [
      # Test Case 1: A failed job with a known error (CSV).
      {
          'project_id': 'gcpdiag-bigquery1-aaaa',
          'bigquery_job_id': 'test_csv_error',
          'bigquery_job_region': 'us',
          'bigquery_skip_permission_check': False,
      },
      # Test Case 2: A failed job with an unknown error.
      {
          'project_id': 'gcpdiag-bigquery1-aaaa',
          'bigquery_job_id': 'test_unknown',
          'bigquery_job_region': 'us',
          'bigquery_skip_permission_check': False,
      },
      # Test Case 3: A job that completed successfully (no error).
      {
          'project_id': 'gcpdiag-bigquery1-aaaa',
          'bigquery_job_id': 'test_success',
          'bigquery_job_region': 'us',
          'bigquery_skip_permission_check': False,
      },
      # Test Case 4: A job that is still running.
      {
          'project_id': 'gcpdiag-bigquery1-aaaa',
          'bigquery_job_id': 'test_running',
          'bigquery_job_region': 'us',
          'bigquery_skip_permission_check': False,
      },
      # Test Case 5: A job ID that does not exist.
      {
          'project_id': 'gcpdiag-bigquery1-aaaa',
          'bigquery_job_id': 'test_notfound',
          'bigquery_job_region': 'us',
          'bigquery_skip_permission_check': False,
      },
      # Test Case 6: An invalid region is provided.
      {
          'project_id': 'gcpdiag-bigquery1-aaaa',
          'bigquery_job_id': 'any_id',
          'bigquery_job_region': 'invalid-region',
          'bigquery_skip_permission_check': False,
      },
  ]


DUMMY_PROJECT_ID = 'gcpdiag-bigquery1-aaaa'


class MockMessage:
  """Mock messages for testing."""

  def get_msg(self, key, **kwargs):
    del kwargs
    return f'{key}'


class FailedQueryStepTestBase(unittest.TestCase):
  """Base class for failed query step tests."""

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
    self.operator.context = models.Context(project_id=DUMMY_PROJECT_ID)

    self.params = {
        flags.PROJECT_ID:
            DUMMY_PROJECT_ID,
        flags.BQ_JOB_REGION:
            'us',
        flags.BQ_JOB_ID:
            'test_success',
        flags.BQ_SKIP_PERMISSION_CHECK:
            True,
        'start_time':
            datetime.datetime(2025, 10, 27, tzinfo=datetime.timezone.utc),
        'end_time':
            datetime.datetime(2025, 10, 28, tzinfo=datetime.timezone.utc),
    }
    self.operator.parameters = self.params


class BigQueryFailedQueryStartTest(FailedQueryStepTestBase):
  """Test BigQueryFailedQueryStart step."""

  def test_valid_parameters(self):
    step = failed_query.BigQueryFailedQueryStart()
    with op.operator_context(self.operator):
      self.operator.set_step(step)
      step.execute()
      self.mock_interface.add_skipped.assert_not_called()
      self.mock_is_enabled.assert_called_once_with(DUMMY_PROJECT_ID, 'bigquery')
      assert op.get(flags.PROJECT_ID) == DUMMY_PROJECT_ID

  @mock.patch('gcpdiag.queries.bigquery.get_bigquery_project')
  def test_get_project_is_none(self, mock_get_project):
    mock_get_project.return_value = None
    step = failed_query.BigQueryFailedQueryStart()
    with op.operator_context(self.operator):
      self.operator.set_step(step)
      step.execute()
    self.mock_interface.add_skipped.assert_called_once()
    self.assertIn(
        'not found or you lack access permissions',
        self.mock_interface.add_skipped.call_args[1]['reason'],
    )

  @mock.patch('gcpdiag.queries.bigquery.get_bigquery_project')
  def test_get_project_api_error_not_found(self, mock_get_project):
    mock_get_project.side_effect = utils.GcpApiError(
        {'message': 'not found or deleted'})
    step = failed_query.BigQueryFailedQueryStart()
    with op.operator_context(self.operator):
      self.operator.set_step(step)
      step.execute()
    self.mock_interface.add_skipped.assert_called_once()
    self.assertIn(
        'not found or deleted',
        self.mock_interface.add_skipped.call_args[1]['reason'],
    )

  @mock.patch('gcpdiag.queries.bigquery.get_bigquery_project')
  def test_get_project_api_error_permission_denied(self, mock_get_project):
    mock_get_project.side_effect = utils.GcpApiError(
        {'message': 'caller does not have required permission to use project'})
    step = failed_query.BigQueryFailedQueryStart()
    with op.operator_context(self.operator):
      self.operator.set_step(step)
      step.execute()
    self.mock_interface.add_skipped.assert_called_once()
    self.assertIn(
        'You do not have permissions',
        self.mock_interface.add_skipped.call_args[1]['reason'],
    )

  @mock.patch('gcpdiag.queries.bigquery.get_bigquery_project')
  def test_get_project_api_error_rm_permission_denied(self, mock_get_project):
    mock_get_project.side_effect = utils.GcpApiError(
        {'message': 'resourcemanager.projects.get denied on resource'})
    step = failed_query.BigQueryFailedQueryStart()
    with op.operator_context(self.operator):
      self.operator.set_step(step)
      step.execute()
      self.mock_interface.info.assert_called_with(mock.ANY, 'INFO')
      self.mock_interface.add_skipped.assert_not_called()
      self.mock_is_enabled.assert_called_once_with(DUMMY_PROJECT_ID, 'bigquery')
      assert op.get(flags.PROJECT_ID) == DUMMY_PROJECT_ID

  def test_invalid_project_id(self):
    self.params[flags.PROJECT_ID] = ''
    step = failed_query.BigQueryFailedQueryStart()
    with op.operator_context(self.operator):
      self.operator.set_step(step)
      step.execute()
    self.mock_interface.add_skipped.assert_called_once()
    self.assertIn(
        'Invalid project identifier',
        self.mock_interface.add_skipped.call_args[1]['reason'],
    )

  def test_invalid_region(self):
    self.params[flags.BQ_JOB_REGION] = 'invalid-region'
    step = failed_query.BigQueryFailedQueryStart()
    with op.operator_context(self.operator):
      self.operator.set_step(step)
      step.execute()
    self.mock_interface.add_skipped.assert_called_once()
    self.assertIn(
        'Invalid job region',
        self.mock_interface.add_skipped.call_args[1]['reason'],
    )

  def test_invalid_job_id(self):
    self.params[flags.BQ_JOB_ID] = ''
    step = failed_query.BigQueryFailedQueryStart()
    with op.operator_context(self.operator):
      self.operator.set_step(step)
      step.execute()
    self.mock_interface.add_skipped.assert_called_once()
    self.assertIn(
        'Invalid job identifier',
        self.mock_interface.add_skipped.call_args[1]['reason'],
    )

  def test_bq_api_not_enabled(self):
    self.mock_is_enabled.return_value = False
    step = failed_query.BigQueryFailedQueryStart()
    with op.operator_context(self.operator):
      self.operator.set_step(step)
      step.execute()
    self.mock_interface.add_skipped.assert_called_once()
    self.assertIn(
        'BigQuery API is not enabled',
        self.mock_interface.add_skipped.call_args[1]['reason'],
    )

  def test_get_user_email_attribute_error(self):
    self.mock_get_user_email.side_effect = AttributeError(
        "'ResourceManager' object has no attribute 'with_quota_project'")
    step = failed_query.BigQueryFailedQueryStart()
    with op.operator_context(self.operator):
      self.operator.set_step(step)
      step.execute()
    self.mock_interface.info.assert_any_call(
        'Running the investigation within the GCA context.', 'INFO')

  def test_is_enabled_api_error(self):
    self.mock_is_enabled.side_effect = utils.GcpApiError(
        {'message': 'access denied'})
    step = failed_query.BigQueryFailedQueryStart()
    with op.operator_context(self.operator):
      self.operator.set_step(step)
      step.execute()
    self.mock_interface.info.assert_called()

  def test_get_user_email_runtime_error(self):
    self.mock_get_user_email.side_effect = RuntimeError(
        'Failed to get credentials')
    step = failed_query.BigQueryFailedQueryStart()
    with op.operator_context(self.operator):
      self.operator.set_step(step)
      step.execute()
    self.mock_interface.info.assert_any_call(
        'Unable to fetch user email. Please make sure to authenticate properly'
        ' before executing the investigation. Attempting to run the'
        ' investigation.',
        'INFO',
    )


class BigQueryJobExistsTest(FailedQueryStepTestBase):
  """Test BigQueryJobExists step."""

  def test_job_exists(self):
    self.params[flags.BQ_JOB_ID] = 'test_success'
    step = failed_query.BigQueryJobExists()
    with op.operator_context(self.operator):
      self.operator.set_step(step)
      step.execute()
    self.mock_interface.add_ok.assert_called_once()
    assert any(
        isinstance(c, failed_query.ConfirmBQJobIsDone) for c in step.steps)

  def test_get_job_not_found_gcp_api_error(self):
    self.params[flags.BQ_JOB_ID] = 'test_notfound_exception'
    step = failed_query.BigQueryJobExists()
    with op.operator_context(self.operator):
      self.operator.set_step(step)
      step.execute()
    self.mock_interface.add_failed.assert_called_once()

  def test_job_not_found(self):
    self.params[flags.BQ_JOB_ID] = 'test_notfound'
    step = failed_query.BigQueryJobExists()
    with op.operator_context(self.operator):
      self.operator.set_step(step)
      step.execute()
    self.mock_interface.add_failed.assert_called_once()

  def test_get_project_error(self):
    self.params[flags.BQ_JOB_ID] = 'test_success'
    step = failed_query.BigQueryJobExists()
    with op.operator_context(self.operator):
      self.operator.set_step(step)
      step.execute()
    self.mock_interface.add_ok.assert_called_once()

  @mock.patch('gcpdiag.queries.bigquery.get_bigquery_project')
  def test_get_project_gcp_api_error_pass(self, mock_get_project):
    mock_get_project.side_effect = utils.GcpApiError('Failed to get project')
    self.params[flags.BQ_JOB_ID] = 'test_notfound'
    step = failed_query.BigQueryJobExists()
    with op.operator_context(self.operator):
      self.operator.set_step(step)
      step.execute()
    self.mock_interface.add_failed.assert_called_once()

  @mock.patch('gcpdiag.queries.bigquery.get_bigquery_job')
  def test_get_job_raises_not_found_gcp_api_error(self, mock_get_job):
    mock_get_job.side_effect = utils.GcpApiError('not found')
    self.params[flags.BQ_JOB_ID] = 'job_raises_notfound'
    step = failed_query.BigQueryJobExists()
    with op.operator_context(self.operator):
      self.operator.set_step(step)
      step.execute()
    self.mock_interface.add_failed.assert_called_once()

  @mock.patch('gcpdiag.queries.bigquery.get_bigquery_job')
  def test_get_job_access_denied_runtime_error(self, mock_get_job):
    mock_get_job.side_effect = utils.GcpApiError('access denied')
    self.mock_get_user_email.side_effect = RuntimeError(
        'Failed to get credentials')
    self.params[flags.BQ_JOB_ID] = 'some_job'
    step = failed_query.BigQueryJobExists()
    with op.operator_context(self.operator):
      self.operator.set_step(step)
      step.execute()
    self.mock_interface.add_skipped.assert_called_once()

  @mock.patch('gcpdiag.queries.bigquery.get_bigquery_job')
  def test_get_job_access_denied_attribute_error(self, mock_get_job):
    mock_get_job.side_effect = utils.GcpApiError('access denied')
    self.mock_get_user_email.side_effect = AttributeError(
        "'ResourceManager' object has no attribute 'with_quota_project'")
    self.params[flags.BQ_JOB_ID] = 'some_job'
    step = failed_query.BigQueryJobExists()
    with op.operator_context(self.operator):
      self.operator.set_step(step)
      step.execute()
    self.mock_interface.add_skipped.assert_called_once()


class ConfirmBQJobIsDoneTest(FailedQueryStepTestBase):
  """Test ConfirmBQJobIsDone step."""

  def test_job_is_done(self):
    self.params[flags.BQ_JOB_ID] = 'test_success'
    step = failed_query.ConfirmBQJobIsDone()
    with op.operator_context(self.operator):
      self.operator.set_step(step)
      step.execute()
    self.mock_interface.add_ok.assert_called_once()

  def test_job_is_not_done(self):
    self.params[flags.BQ_JOB_ID] = 'test_running'
    step = failed_query.ConfirmBQJobIsDone()
    with op.operator_context(self.operator):
      self.operator.set_step(step)
      step.execute()
    self.mock_interface.add_failed.assert_called_once()

  def test_job_is_none(self):
    self.params[flags.BQ_JOB_ID] = 'test_notfound'
    step = failed_query.ConfirmBQJobIsDone()
    with op.operator_context(self.operator):
      self.operator.set_step(step)
      step.execute()
    self.mock_interface.add_skipped.assert_called_once()


class CheckBQJobHasFailedTest(FailedQueryStepTestBase):
  """Test CheckBQJobHasFailed step."""

  def test_job_has_failed(self):
    self.params[flags.BQ_JOB_ID] = 'test_with_error'
    step = failed_query.CheckBQJobHasFailed()
    with op.operator_context(self.operator):
      self.operator.set_step(step)
      step.execute()
    self.mock_interface.add_ok.assert_called_once()

  def test_job_has_not_failed(self):
    self.params[flags.BQ_JOB_ID] = 'test_success'
    step = failed_query.CheckBQJobHasFailed()
    with op.operator_context(self.operator):
      self.operator.set_step(step)
      step.execute()
    self.mock_interface.add_skipped.assert_called_once()

  def test_job_is_none(self):
    self.params[flags.BQ_JOB_ID] = 'test_notfound'
    step = failed_query.CheckBQJobHasFailed()
    with op.operator_context(self.operator):
      self.operator.set_step(step)
      step.execute()
    self.mock_interface.add_skipped.assert_called_once()

  def test_known_error_in_job_errors(self):
    self.params[flags.BQ_JOB_ID] = 'test_job_errors'
    step = failed_query.BigQueryErrorIdentification()
    with op.operator_context(self.operator):
      self.operator.set_step(step)
      step.execute()
    self.mock_interface.add_failed.assert_called_once()

  def test_no_error_message_in_job(self):
    self.params[flags.BQ_JOB_ID] = 'test_no_error_message_in_job'
    step = failed_query.BigQueryErrorIdentification()
    with op.operator_context(self.operator):
      self.operator.set_step(step)
      step.execute()
    self.mock_interface.add_uncertain.assert_called_once()


class BigQueryErrorIdentificationTest(FailedQueryStepTestBase):
  """Test BigQueryErrorIdentification step."""

  def test_known_error(self):
    self.params[flags.BQ_JOB_ID] = 'test_csv_error'
    step = failed_query.BigQueryErrorIdentification()
    with op.operator_context(self.operator):
      self.operator.set_step(step)
      step.execute()
    self.mock_interface.add_failed.assert_called_once()

  def test_unknown_error(self):
    self.params[flags.BQ_JOB_ID] = 'test_unknown'
    step = failed_query.BigQueryErrorIdentification()
    with op.operator_context(self.operator):
      self.operator.set_step(step)
      step.execute()
    self.mock_interface.add_uncertain.assert_called_once()

  def test_job_is_none(self):
    self.params[flags.BQ_JOB_ID] = 'test_notfound'
    step = failed_query.BigQueryErrorIdentification()
    with op.operator_context(self.operator):
      self.operator.set_step(step)
      step.execute()
    self.mock_interface.add_skipped.assert_called_once()

  def test_job_error_result_is_none(self):
    self.params[flags.BQ_JOB_ID] = 'test_success'
    step = failed_query.BigQueryErrorIdentification()
    with op.operator_context(self.operator):
      self.operator.set_step(step)
      step.execute()
    self.mock_interface.add_skipped.assert_called_once()

  def test_duplicate_error_messages(self):
    self.params[flags.BQ_JOB_ID] = 'test_duplicate'
    step = failed_query.BigQueryErrorIdentification()
    with op.operator_context(self.operator):
      self.operator.set_step(step)
      step.execute()
    self.mock_interface.add_uncertain.assert_called_once()


class BigQueryEndTest(FailedQueryStepTestBase):
  """Test BigQueryEnd step."""

  def test_end_step(self):
    step = failed_query.BigQueryEnd()
    with op.operator_context(self.operator):
      self.operator.set_step(step)
      step.execute()
    self.mock_interface.info.assert_called_with('No more checks to perform.',
                                                'INFO')

  def test_no_error_message_found(self):
    self.params[flags.BQ_JOB_ID] = 'test_no_error_found'
    step = failed_query.BigQueryErrorIdentification()
    with op.operator_context(self.operator):
      self.operator.set_step(step)
      step.execute()
    self.mock_interface.add_skipped.assert_called_once()


class FailedQueryTest(unittest.TestCase):

  def test_build_tree(self):
    dq = failed_query.FailedQuery()
    dq.build_tree()
    self.assertIsInstance(dq.start, failed_query.BigQueryFailedQueryStart)
    start_step_children = dq.start.steps
    self.assertEqual(len(start_step_children), 2)
    permission_check_step = start_step_children[0]
    self.assertIsInstance(
        permission_check_step,
        failed_query.bigquery_gs.RunPermissionChecks,
    )
    permission_check_step_children = permission_check_step.steps
    self.assertEqual(len(permission_check_step_children), 1)
    job_exists_step = permission_check_step_children[0]
    self.assertIsInstance(job_exists_step, failed_query.BigQueryJobExists)
    end_step = start_step_children[1]
    self.assertIsInstance(end_step, failed_query.BigQueryEnd)
