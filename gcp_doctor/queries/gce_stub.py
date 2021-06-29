# Lint as: python3
"""Stub API calls used in gce.py for testing.

Instead of doing real API calls, we return test JSON data.
"""

import copy
import json
import pathlib

# pylint: disable=unused-argument

JSON_PROJECT_DIR = {
    'gcpd-gce1-4exv':
        pathlib.Path(__file__).parents[2] / 'test-data/gce1/json-dumps',
    'gcpd-gke-1-9b90':
        pathlib.Path(__file__).parents[2] / 'test-data/gke1/json-dumps',
}

INSTANCES_ZONES = {
    'gcpd-gce1-4exv': ['europe-west1-b', 'europe-west4-a'],
    'gcpd-gke-1-9b90': ['europe-west4-a'],
}


class BatchRequestStub:
  """Mock object returned by new_batch_http_request()."""

  def __init__(self):
    self.queue = []

  def add(self, operation, callback, request_id=None):
    self.queue.append((copy.deepcopy(operation), callback, request_id))
    return self

  def execute(self):
    for op in self.queue:
      if op[0].mock_state in ['migs', 'instances']:
        if op[0].zone in INSTANCES_ZONES[op[0].project_id]:
          if op[0].page == 1:
            json_file_path = f'{JSON_PROJECT_DIR[op[0].project_id]}/'+\
                f'compute-{op[0].mock_state}-{op[0].zone}.json'
          else:
            json_file_path = f'{JSON_PROJECT_DIR[op[0].project_id]}/'+\
                f'compute-{op[0].mock_state}-{op[0].zone}-{op[0].page}.json'
        else:
          json_file_path = f'{JSON_PROJECT_DIR[op[0].project_id]}/'+\
              f'compute-{op[0].mock_state}-empty.json'
        with open(json_file_path) as json_file:
          response = json.load(json_file)
          op[1](op[2], response, None)
      else:
        raise ValueError(
            'can\'t use batch request with methods other than'+\
            f'instances and instanceGroupManagers ({op[0].mock_state})'
        )


class ComputeEngineApiStub:
  """Mock object to simulate compute engine api calls."""

  # mocked methods:
  # gce_api.zones().list(project=project_id).execute()
  # gce_api.zones().list_next(request, response)
  # op1=gce_api.instances().list(project=pid, zone=z)
  # gce_api.new_batch_http_request().add(op1, callback=cb, request_id=id).execute()
  # gce_api.instanceGroupManagers().list(project=project_id, zone=zone)

  def __init__(self, mock_state='init', project_id=None, zone=None, page=1):
    self.mock_state = mock_state
    self.project_id = project_id
    self.zone = zone
    self.page = page

  def zones(self):
    return ComputeEngineApiStub('zones')

  def list(self, project, zone=None):
    return ComputeEngineApiStub(self.mock_state, project_id=project, zone=zone)

  def list_next(self, request, response):
    if self.mock_state == 'instances' and request.zone == 'europe-west1-b' and request.page == 1:
      return ComputeEngineApiStub(mock_state='instances',
                                  project_id=request.project_id,
                                  zone=request.zone,
                                  page=request.page + 1)
    else:
      return None

  def instances(self):
    return ComputeEngineApiStub('instances')

  # pylint: disable=invalid-name
  def instanceGroupManagers(self):
    return ComputeEngineApiStub('migs')

  def new_batch_http_request(self):
    return BatchRequestStub()

  def execute(self, num_retries=0):
    if self.mock_state == 'zones':
      with open(f'{JSON_PROJECT_DIR[self.project_id]}/compute-zones.json'
               ) as json_file:
        return json.load(json_file)
    else:
      raise ValueError("can't call this method here")


def get_api_stub(service_name: str, version: str):
  return ComputeEngineApiStub()
