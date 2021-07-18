# Copyright 2021 Google LLC
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

# Lint as: python3
"""Stub API calls used in monitoring.py for testing.

Instead of doing real API calls, we return test JSON data.
"""

import json
import pathlib

# pylint: disable=unused-argument

JSON_DUMPS_PATH = pathlib.Path(
    __file__).parents[2] / 'test-data/gce1/json-dumps'
QUERY_JSON = JSON_DUMPS_PATH / 'monitoring-query.json'


class MonitoringApiStub:
  """Mock object to simulate monitoring.googleapis.com calls."""

  def projects(self):
    return self

  # pylint: disable=invalid-name
  def timeSeries(self):
    return self

  def query(self, name, body):
    del name
    del body
    return self

  def query_next(self, previous_request, previous_response):
    del previous_request
    del previous_response

  def execute(self, num_retries=0):
    with open(QUERY_JSON) as json_file:
      return json.load(json_file)


def get_api_stub(service_name: str, version: str):
  return MonitoringApiStub()
