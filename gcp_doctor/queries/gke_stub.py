# Lint as: python3
"""Stub API calls used in gke.py for testing.

Instead of doing real API calls, we return test JSON data.
"""

import json
import pathlib

# pylint: disable=unused-argument

CLUSTERS_LIST_JSON = pathlib.Path(
    __file__).parents[2] / 'test-data/gke1/json-dumps/clusters.json'


class ContainerApiStub:
  """Mock object to simulate container api calls."""

  def projects(self):
    return self

  def locations(self):
    return self

  def clusters(self):
    return self

  def list(self, parent=None):
    return self

  def execute(self, num_retries=0):
    with open(CLUSTERS_LIST_JSON) as json_file:
      return json.load(json_file)


def get_api_stub(service_name: str, version: str):
  return ContainerApiStub()
