"""Test code in dataflow.py."""

from unittest import mock

from gcpdiag import models
from gcpdiag.queries import apis_stub, dataflow

DUMMY_PROJECT_NAME = 'gcpdiag-dataflow1-aaaa'


@mock.patch('gcpdiag.queries.apis.get_api', new=apis_stub.get_api_stub)
class TestDataFlow:
  """Test Dataflow"""

  def test_get_jobs(self):
    context = models.Context(project_id=DUMMY_PROJECT_NAME)
    jobs = dataflow.get_all_dataflow_jobs(context)
    assert {j.state for j in jobs} != {'JOB_STATE_FAILED'}
    assert None not in [j.minutes_in_current_state for j in jobs]

  def test_get_jobs_with_id(self):
    context = models.Context(
        project_id=DUMMY_PROJECT_NAME  #,
        # labels={'id': '2022-09-19_09_20_57-11848816011797209899'})
    )
    jobs = dataflow.get_all_dataflow_jobs(context=context)
    assert len(jobs) != 0
    sample_job = dataflow.get_job(project_id=context.project_id,
                                  job=jobs[0].id,
                                  region='us-central1')
    assert sample_job is not None
