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
    assert {j.state for j in jobs} == {'JOB_STATE_DONE'}
    assert None not in [j.minutes_in_current_state for j in jobs]
