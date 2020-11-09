# Lint as: python3
"""Mock functionality of gke.py for testing."""

import json
import pathlib

# pylint: disable=unused-argument

CLUSTERS_LIST_DUMMY = pathlib.Path(
    __file__).parents[2] / 'dummies/gke1/json-dumps/clusters.json'


class ContainerApiMocked:
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
    with open(CLUSTERS_LIST_DUMMY) as json_file:
      return json.load(json_file)


def get_api_mocked(service_name: str, version: str):
  return ContainerApiMocked()
