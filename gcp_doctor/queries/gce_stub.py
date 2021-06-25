# Lint as: python3
"""Stub API calls used in gce.py for testing.

Instead of doing real API calls, we return test JSON data.
"""

import copy
import json
import pathlib

# pylint: disable=unused-argument

JSON_DUMPS_PATH = pathlib.Path(
    __file__).parents[2] / 'test-data/gce1/json-dumps'
ZONES_LIST_JSON = JSON_DUMPS_PATH / 'zones.json'
INSTANCES_ZONES = ['europe-west1-b', 'europe-west4-a']


class BatchRequestStub:
  """Mock object returned by new_batch_http_request()."""

  def __init__(self):
    self.queue = []

  def add(self, operation, callback, request_id=None):
    self.queue.append((copy.deepcopy(operation), callback, request_id))
    return self

  def execute(self):
    for op in self.queue:
      if op[0].mock_state != 'instances':
        raise ValueError(
            f"can't use batch request with methods other than instances ({op[0].mock_state})"
        )

      if op[0].zone in INSTANCES_ZONES:
        if op[0].page == 1:
          instances_list_file = JSON_DUMPS_PATH / f'instances-{op[0].zone}.json'
        else:
          instances_list_file = JSON_DUMPS_PATH / f'instances-{op[0].zone}-{op[0].page}.json'
      else:
        instances_list_file = JSON_DUMPS_PATH / 'instances-empty.json'

      with open(instances_list_file) as json_file:
        response = json.load(json_file)
        op[1](op[2], response, None)


class ComputeEngineApiStub:
  """Mock object to simulate compute engine api calls."""

  # mocked methods:
  # gce_api.zones().list(project=project_id).execute()
  # gce_api.zones().list_next(request, response)
  # op1=gce_api.instances().list(project=pid, zone=z)
  # gce_api.new_batch_http_request().add(op1, callback=cb, request_id=id).execute()

  def __init__(self, mock_state='init', zone=None, page=1):
    self.mock_state = mock_state
    self.zone = zone
    self.page = page

  def zones(self):
    return ComputeEngineApiStub('zones')

  def list(self, project, zone=None):
    return ComputeEngineApiStub(self.mock_state, zone)

  def list_next(self, request, response):
    if request.zone == 'europe-west1-b' and request.page == 1:
      return ComputeEngineApiStub('instances', request.zone, request.page + 1)
    else:
      return None

  def instances(self):
    return ComputeEngineApiStub('instances')

  def new_batch_http_request(self):
    return BatchRequestStub()

  def execute(self, num_retries=0):
    if self.mock_state == 'zones':
      with open(ZONES_LIST_JSON) as json_file:
        return json.load(json_file)
    else:
      raise ValueError("can't call this method here")


def get_api_stub(service_name: str, version: str):
  return ComputeEngineApiStub()
