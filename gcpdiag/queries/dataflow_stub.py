"""
Mocks to simulate Dataflow API calls.
"""

from gcpdiag.queries import apis_stub


class DataflowApiStub(apis_stub.ApiStub):
  """Mock object to simulate instance api calls."""

  def projects(self):
    return self

  def locations(self):
    return self

  def jobs(self):
    return DataflowJobsListStub()


class DataflowJobsListStub:

  # pylint: disable=invalid-name
  def list(self, projectId, location):
    return apis_stub.RestCallStub(projectId,
                                  f'dataflow-jobs-{location}',
                                  default={})

  def list_next(self, previous_request, previous_response):
    pass
