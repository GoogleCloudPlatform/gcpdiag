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
"""Stub API calls used in monitoring.py for testing.

Instead of doing real API calls, we return test JSON data.
"""

import json
import re

from gcpdiag.queries import apis_stub

# pylint: disable=unused-argument


class MonitoringApiStub:
  """Mock object to simulate monitoring.googleapis.com calls."""

  def projects(self):
    return self

  # pylint: disable=invalid-name
  def timeSeries(self):
    return self

  def query(self, name, body):
    del body
    m = re.match(r'projects/([^/]+)', name)
    self.project_id = m.group(1)
    return self

  def query_next(self, previous_request, previous_response):
    del previous_request
    del previous_response

  def execute(self, num_retries=0):
    json_dir = apis_stub.get_json_dir(self.project_id)
    with open(json_dir / 'monitoring-query.json',
              encoding='utf-8') as json_file:
      return json.load(json_file)
