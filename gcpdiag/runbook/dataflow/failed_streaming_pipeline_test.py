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
"""Test class for dataflow/Failed_streaming_pipeline."""

import datetime
import unittest
from unittest import mock

from absl.testing import parameterized

from gcpdiag import config
from gcpdiag.queries import apis_stub, dataflow
from gcpdiag.runbook import dataflow as dataflow_rb
from gcpdiag.runbook import op, snapshot_test_base
from gcpdiag.runbook.dataflow import failed_streaming_pipeline, flags

DUMMY_PROJECT_ID = 'gcpdiag-dataflow1-aaaa'
DUMMY_JOB_ID = '2024-06-19_09_43_07-14927685200167458422'
DUMMY_REGION = 'us-central1'


class Test(snapshot_test_base.RulesSnapshotTestBase):
  rule_pkg = dataflow_rb
  runbook_name = 'dataflow/failed-streaming-pipeline'
  config.init({'auto': True, 'interface': 'cli'})

  rule_parameters = [{
      'project_id': DUMMY_PROJECT_ID,
      'dataflow_job_id': DUMMY_JOB_ID,
      'job_region': DUMMY_REGION,
  }]


class MockMessage:
  """Mock messages for testing."""

  def get_msg(self, key, **kwargs):
    del kwargs
    return f'{key}'


class FailedStreamingPipelineTest(unittest.TestCase):

  def test_legacy_parameter_handler(self):
    runbook = failed_streaming_pipeline.FailedStreamingPipeline()
    parameters = {
        'job_id': 'test-job-id',
        'project_id': 'test-project',
        'job_region': 'us-central1',
    }
    runbook.legacy_parameter_handler(parameters)
    self.assertNotIn('job_id', parameters)
    self.assertIn('dataflow_job_id', parameters)
    self.assertEqual(parameters['dataflow_job_id'], 'test-job-id')


class FailedStreamingPipelineBuildTreeTest(unittest.TestCase):

  @mock.patch(
      'gcpdiag.runbook.dataflow.failed_streaming_pipeline.FailedStreamingPipeline.add_step'
  )
  @mock.patch(
      'gcpdiag.runbook.dataflow.failed_streaming_pipeline.FailedStreamingPipeline.add_start'
  )
  @mock.patch(
      'gcpdiag.runbook.dataflow.failed_streaming_pipeline.FailedStreamingPipeline.add_end'
  )
  @mock.patch('gcpdiag.runbook.op.get')
  def test_build_tree(self, mock_op_get, mock_add_end, mock_add_start,
                      mock_add_step):
    mock_op_get.return_value = 'test_value'
    runbook = failed_streaming_pipeline.FailedStreamingPipeline()
    runbook.build_tree()
    mock_add_start.assert_called_once()
    self.assertIsInstance(
        mock_add_start.call_args[0][0],
        failed_streaming_pipeline.FailedStreamingPipelineStart,
    )
    steps_added = [call[1]['child'] for call in mock_add_step.call_args_list]
    self.assertTrue(
        any(
            isinstance(s, failed_streaming_pipeline.JobIsStreaming)
            for s in steps_added))
    self.assertTrue(
        any(
            isinstance(s, dataflow_rb.generalized_steps.ValidSdk)
            for s in steps_added))
    self.assertTrue(
        any(
            isinstance(s, failed_streaming_pipeline.JobGraphIsConstructed)
            for s in steps_added))
    mock_add_end.assert_called_once()
    self.assertIsInstance(
        mock_add_end.call_args[0][0],
        failed_streaming_pipeline.FailedStreamingPipelineEnd,
    )


class FailedStreamingPipelineStepTestBase(unittest.TestCase):
  """Base class for Failed Streaming Pipeline step tests."""

  def setUp(self):
    super().setUp()
    # 1. Patch get_api with the stub.
    self.enterContext(
        mock.patch('gcpdiag.queries.apis.get_api', new=apis_stub.get_api_stub))
    # 2. Create a mock interface to capture outputs
    self.mock_interface = mock.create_autospec(op.InteractionInterface,
                                               instance=True)
    self.mock_interface.rm = mock.Mock()
    # 3. Instantiate a real Operator
    self.operator = op.Operator(self.mock_interface)
    self.operator.run_id = 'test-run'
    self.operator.messages = MockMessage()
    # 4. Define standard parameters.
    self.params = {
        flags.PROJECT_ID:
            DUMMY_PROJECT_ID,
        flags.DATAFLOW_JOB_ID:
            DUMMY_JOB_ID,
        flags.JOB_REGION:
            DUMMY_REGION,
        'start_time':
            datetime.datetime(2025, 1, 1, tzinfo=datetime.timezone.utc),
        'end_time':
            datetime.datetime(2025, 1, 2, tzinfo=datetime.timezone.utc),
    }
    self.operator.parameters = self.params
    self.mock_op_prompt = self.enterContext(
        mock.patch('gcpdiag.runbook.op.prompt'))


class FailedStreamingPipelineStartTest(FailedStreamingPipelineStepTestBase):
  """Test FailedStreamingPipelineStart step."""

  @mock.patch('gcpdiag.queries.dataflow.get_job')
  def test_start_step_ok(self, mock_get_job):
    mock_get_job.return_value = mock.Mock(spec=dataflow.Job)
    step = failed_streaming_pipeline.FailedStreamingPipelineStart()
    with op.operator_context(self.operator):
      self.operator.set_step(step)
      step.execute()
    self.mock_interface.add_ok.assert_called_once()
    self.mock_interface.add_skipped.assert_not_called()

  @mock.patch('gcpdiag.queries.apis.is_enabled', return_value=False)
  def test_start_step_api_disabled(self, mock_is_enabled):
    step = failed_streaming_pipeline.FailedStreamingPipelineStart()
    with op.operator_context(self.operator):
      self.operator.set_step(step)
      step.execute()
    self.assertEqual(mock_is_enabled.call_count, 2)
    mock_is_enabled.assert_called_with(DUMMY_PROJECT_ID, 'dataflow')
    self.assertEqual(self.mock_interface.add_skipped.call_count, 2)

  @mock.patch('gcpdiag.queries.dataflow.get_job', return_value=None)
  def test_start_step_job_not_found(self, mock_get_job):
    del mock_get_job
    self.params[flags.DATAFLOW_JOB_ID] = 'non-existent-job'
    step = failed_streaming_pipeline.FailedStreamingPipelineStart()
    with op.operator_context(self.operator):
      self.operator.set_step(step)
      step.execute()
    self.mock_interface.add_skipped.assert_called_once()
    self.mock_interface.add_ok.assert_not_called()


class JobIsStreamingTest(FailedStreamingPipelineStepTestBase):
  """Test JobIsStreaming step."""

  @mock.patch('gcpdiag.queries.dataflow.get_job')
  def test_job_is_streaming(self, mock_get_job):
    mock_job = mock.Mock(spec=dataflow.Job)
    mock_job.job_type = 'JOB_TYPE_STREAMING'
    mock_get_job.return_value = mock_job
    step = failed_streaming_pipeline.JobIsStreaming()
    with op.operator_context(self.operator):
      self.operator.set_step(step)
      step.execute()
    self.mock_interface.add_ok.assert_called_once()
    self.mock_interface.add_failed.assert_not_called()

  @mock.patch('gcpdiag.queries.dataflow.get_job')
  def test_job_is_not_streaming(self, mock_get_job):
    mock_job = mock.Mock(spec=dataflow.Job)
    mock_job.job_type = 'JOB_TYPE_BATCH'
    mock_get_job.return_value = mock_job
    step = failed_streaming_pipeline.JobIsStreaming()
    with op.operator_context(self.operator):
      self.operator.set_step(step)
      step.execute()
    self.mock_interface.add_failed.assert_called_once()
    self.mock_interface.add_ok.assert_not_called()


class JobStateTest(FailedStreamingPipelineStepTestBase, parameterized.TestCase):
  """Test JobState step."""

  @mock.patch('gcpdiag.queries.logs.query')
  @mock.patch('gcpdiag.queries.dataflow.get_job')
  def test_job_state_failed_no_error_logs(self, mock_get_job, mock_logs_query):
    mock_job = mock.Mock(spec=dataflow.Job, state='JOB_STATE_FAILED')
    mock_get_job.return_value = mock_job
    mock_logs_query.return_value = mock.Mock(entries=[])
    step = failed_streaming_pipeline.JobState()
    with op.operator_context(self.operator):
      self.operator.set_step(step)
      step.execute()
    mock_logs_query.assert_called_once()
    self.mock_interface.info.assert_not_called()
    self.mock_interface.add_failed.assert_called_once()

  @mock.patch('gcpdiag.queries.logs.query')
  @mock.patch('gcpdiag.queries.dataflow.get_job')
  def test_job_state_failed_with_error_logs(self, mock_get_job,
                                            mock_logs_query):
    mock_job = mock.Mock(spec=dataflow.Job, state='JOB_STATE_FAILED')
    mock_get_job.return_value = mock_job
    mock_logs_query.return_value = mock.Mock(entries=[{
        'severity': 'ERROR',
        'message': 'error log'
    }])
    step = failed_streaming_pipeline.JobState()
    with op.operator_context(self.operator):
      self.operator.set_step(step)
      step.execute()
    mock_logs_query.assert_called_once()
    self.mock_interface.info.assert_called_once()
    self.mock_interface.add_failed.assert_called_once()

  @mock.patch('gcpdiag.queries.dataflow.get_job')
  def test_job_state_stopped(self, mock_get_job):
    mock_job = mock.Mock(spec=dataflow.Job, state='JOB_STATE_STOPPED')
    mock_get_job.return_value = mock_job
    step = failed_streaming_pipeline.JobState()
    with op.operator_context(self.operator):
      self.operator.set_step(step)
      step.execute()
    self.mock_interface.add_uncertain.assert_called_once()

  @parameterized.parameters('JOB_STATE_CANCELLED', 'JOB_STATE_RUNNING')
  @mock.patch('gcpdiag.queries.dataflow.get_job')
  def test_job_state_ok(self, job_state, mock_get_job):
    mock_job = mock.Mock(spec=dataflow.Job, state=job_state)
    mock_get_job.return_value = mock_job
    step = failed_streaming_pipeline.JobState()
    with op.operator_context(self.operator):
      self.operator.set_step(step)
      step.execute()
    self.mock_interface.add_failed.assert_not_called()
    self.mock_interface.add_uncertain.assert_not_called()


class JobGraphIsConstructedTest(FailedStreamingPipelineStepTestBase):
  """Test JobGraphIsConstructed step."""

  def setUp(self):
    super().setUp()
    self.add_child_patch = self.enterContext(
        mock.patch(
            'gcpdiag.runbook.dataflow.failed_streaming_pipeline.JobGraphIsConstructed.add_child'
        ))

  @mock.patch('gcpdiag.queries.dataflow.get_job')
  def test_graph_construction_error_yes(self, mock_get_job):
    mock_job = mock.Mock(spec=dataflow.Job)
    mock_job.sdk_language = 'java'
    mock_get_job.return_value = mock_job
    self.mock_op_prompt.return_value = op.YES
    step = failed_streaming_pipeline.JobGraphIsConstructed()
    with op.operator_context(self.operator):
      self.operator.set_step(step)
      step.execute()
    self.mock_op_prompt.assert_called_once()
    self.mock_interface.add_failed.assert_called_once()
    self.add_child_patch.assert_called_once()
    self.assertIsInstance(
        self.add_child_patch.call_args[1]['child'],
        failed_streaming_pipeline.FailedStreamingPipelineEnd,
    )

  @mock.patch('gcpdiag.queries.dataflow.get_job')
  def test_graph_construction_error_no(self, mock_get_job):
    mock_job = mock.Mock(spec=dataflow.Job)
    mock_job.sdk_language = 'java'
    mock_get_job.return_value = mock_job
    self.mock_op_prompt.return_value = op.NO
    step = failed_streaming_pipeline.JobGraphIsConstructed()
    with op.operator_context(self.operator):
      self.operator.set_step(step)
      step.execute()
    self.mock_op_prompt.assert_called_once()
    self.mock_interface.add_failed.assert_not_called()
    self.add_child_patch.assert_called_once()
    self.assertIsInstance(
        self.add_child_patch.call_args[1]['child'],
        failed_streaming_pipeline.JobLogsVisible,
    )

  @mock.patch('gcpdiag.queries.dataflow.get_job')
  def test_graph_construction_error_python_sdk(self, mock_get_job):
    mock_job = mock.Mock(spec=dataflow.Job)
    mock_job.sdk_language = 'python'
    mock_get_job.return_value = mock_job
    self.mock_op_prompt.return_value = op.NO
    step = failed_streaming_pipeline.JobGraphIsConstructed()
    with op.operator_context(self.operator):
      self.operator.set_step(step)
      step.execute()
    self.mock_op_prompt.assert_called_once()
    self.assertIn('TypeCheckError', self.mock_op_prompt.call_args[1]['message'])
    self.mock_interface.add_failed.assert_not_called()
    self.add_child_patch.assert_called_once()
    self.assertIsInstance(
        self.add_child_patch.call_args[1]['child'],
        failed_streaming_pipeline.JobLogsVisible,
    )

  @mock.patch('gcpdiag.queries.dataflow.get_job')
  def test_graph_construction_error_go_sdk(self, mock_get_job):
    mock_job = mock.Mock(spec=dataflow.Job)
    mock_job.sdk_language = 'go'
    mock_get_job.return_value = mock_job
    self.mock_op_prompt.return_value = op.NO
    step = failed_streaming_pipeline.JobGraphIsConstructed()
    with op.operator_context(self.operator):
      self.operator.set_step(step)
      step.execute()
    self.mock_op_prompt.assert_called_once()
    self.assertIn('panic: Method', self.mock_op_prompt.call_args[1]['message'])
    self.mock_interface.add_failed.assert_not_called()
    self.add_child_patch.assert_called_once()
    self.assertIsInstance(
        self.add_child_patch.call_args[1]['child'],
        failed_streaming_pipeline.JobLogsVisible,
    )


class JobLogsVisibleTest(FailedStreamingPipelineStepTestBase):
  """Test JobLogsVisible step."""

  @mock.patch('gcpdiag.queries.dataflow.logs_excluded', return_value=False)
  def test_logs_not_excluded(self, mock_logs_excluded):
    step = failed_streaming_pipeline.JobLogsVisible()
    with op.operator_context(self.operator):
      self.operator.set_step(step)
      step.execute()
    mock_logs_excluded.assert_called_once_with(DUMMY_PROJECT_ID)
    self.mock_interface.add_ok.assert_called_once()
    self.mock_interface.add_failed.assert_not_called()

  @mock.patch('gcpdiag.queries.dataflow.logs_excluded', return_value=None)
  def test_logs_api_disabled(self, mock_logs_excluded):
    step = failed_streaming_pipeline.JobLogsVisible()
    with op.operator_context(self.operator):
      self.operator.set_step(step)
      step.execute()
    mock_logs_excluded.assert_called_once_with(DUMMY_PROJECT_ID)
    self.mock_interface.add_ok.assert_called_once()
    self.mock_interface.add_failed.assert_not_called()

  @mock.patch('gcpdiag.queries.dataflow.logs_excluded',
              side_effect=[True, None])
  def test_logs_excluded_is_none_on_second_call(self, mock_logs_excluded):
    step = failed_streaming_pipeline.JobLogsVisible()
    with op.operator_context(self.operator):
      self.operator.set_step(step)
      step.execute()
    self.assertEqual(mock_logs_excluded.call_count, 2)
    self.mock_interface.add_failed.assert_called_once()
    self.assertEqual(self.mock_interface.add_failed.call_args[1]['resource'],
                     None)
    self.mock_interface.add_ok.assert_not_called()

  @mock.patch('gcpdiag.queries.dataflow.logs_excluded', return_value=True)
  def test_logs_excluded(self, mock_logs_excluded):
    step = failed_streaming_pipeline.JobLogsVisible()
    with op.operator_context(self.operator):
      self.operator.set_step(step)
      step.execute()
    mock_logs_excluded.assert_called_with(DUMMY_PROJECT_ID)
    self.mock_interface.add_failed.assert_called_once()
    self.mock_interface.add_ok.assert_not_called()


class FailedStreamingPipelineEndTest(FailedStreamingPipelineStepTestBase):
  """Test FailedStreamingPipelineEnd step."""

  def test_end_step(self):
    step = failed_streaming_pipeline.FailedStreamingPipelineEnd()
    with op.operator_context(self.operator):
      self.operator.set_step(step)
      step.execute()
    self.mock_interface.info.assert_called_once()


if __name__ == '__main__':
  unittest.main()
