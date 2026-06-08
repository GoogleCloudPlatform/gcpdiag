"""Mocks to simulate Dataflow API calls."""

from gcpdiag.queries import apis_stub


class DataflowApiStub(apis_stub.ApiStub):
  """Mock object to simulate instance api calls."""

  def projects(self):
    return self

  def locations(self):
    return self

  def jobs(self):
    return DataflowJobsStub()


class DataflowJobsStub:
  """Stub for Testing Dataflow."""

  def list(self, projectId, location):
    return apis_stub.RestCallStub(projectId, f'dataflow-jobs-{location}', default={})

  def list_next(self, previous_request, previous_response):
    pass

  def get(self, projectId, location, jobId):
    # BATCH JOB
    if '2026-05-18_07_03_26-5088364741087117679' in jobId:
      return apis_stub.RestCallStub(projectId, f'dataflow-jobs-{location}-batch')
    return apis_stub.RestCallStub(projectId, f'dataflow-jobs-{location}-streaming')

  def aggregated(
    self,
    projectId,
    filter=None,
  ):
    return apis_stub.RestCallStub(projectId, 'dataflow-jobs-aggregated')

  def aggregated_next(self, previous_request, previous_response):
    if isinstance(previous_response, dict) and previous_response.get('nextPageToken'):
      return apis_stub.RestCallStub(
        project_id=previous_request.project_id,
        json_basename=previous_request.json_basename,
        page=previous_request.page + 1,
      )
    else:
      return None
