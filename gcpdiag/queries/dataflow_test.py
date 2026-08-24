"""Test code in dataflow.py."""

import unittest
from unittest import mock

from gcpdiag import models
from gcpdiag.queries import apis_stub, dataflow

DUMMY_PROJECT_NAME = 'gcpdiag-dataflow1-aaaa'


@mock.patch('gcpdiag.queries.apis.get_api', new=apis_stub.get_api_stub)
class TestDataFlow(unittest.TestCase):
  """Test Dataflow."""

  def test_get_jobs(self):
    context = models.Context(project_id=DUMMY_PROJECT_NAME)
    jobs = dataflow.get_all_dataflow_jobs(context)
    assert {j.state for j in jobs} != {'JOB_STATE_FAILED'}
    assert None not in [j.minutes_in_current_state for j in jobs]

  def test_get_jobs_with_id(self):
    context = models.Context(
      project_id=DUMMY_PROJECT_NAME  # ,
      # labels={'id': '2022-09-19_09_20_57-11848816011797209899'})
    )
    jobs = dataflow.get_all_dataflow_jobs(context=context)
    assert len(jobs) != 0
    sample_job = dataflow.get_job(
      project_id=context.project_id, job=jobs[0].id, region='us-central1'
    )
    assert sample_job is not None

  def test_get_jobs_for_project(self):
    jobs = dataflow.get_all_dataflow_jobs_for_project(DUMMY_PROJECT_NAME)
    assert {j.state for j in jobs} != {'JOB_STATE_FAILED'}
    assert None not in [j.minutes_in_current_state for j in jobs]

  def test_streaming_engine_detection(self):
    # Test job without streaming engine
    job_no_se = dataflow.get_job(
      project_id=DUMMY_PROJECT_NAME,
      job='2024-06-19_09_43_07-14927685200167458422',
      region='us-central1',
    )
    assert job_no_se is not None
    assert not job_no_se.is_streaming_engine_enabled

    # Test job with streaming engine
    job_se = dataflow.get_job(
      project_id=DUMMY_PROJECT_NAME, job='streaming-se', region='us-central1'
    )
    assert job_se is not None
    assert job_se.is_streaming_engine_enabled
