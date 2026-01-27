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

import re

from gcpdiag.queries import apis_stub

# pylint: disable=unused-argument


class MonitoringApiStub:
  """Mock object to simulate monitoring.googleapis.com calls."""

  def location(self):
    return self

  def prometheus(self):
    return self

  def projects(self):
    return self

  # pylint: disable=invalid-name
  def timeSeries(self):
    return self

  def api(self):
    return self

  def v1(self):
    return self

  def query_range(self, name, location, body):
    m = re.match(r'projects/([^/]+)', name)
    project_id = m.group(1) if m else 'unknown-project'
    return apis_stub.RestCallStub(
        project_id=project_id,
        json_basename='monitoring-query-range',
        default={
            'status': 'success',
            'data': {
                'resultType':
                    'matrix',
                'result': [{
                    'metric': {
                        '__name__': 'vpn_gateway_tunnel_is_up',
                        'tunnel_id': 'tunnel-abc-123',
                        'project_id': project_id
                    },
                    'values': [[1621438831, '0'], [1621439131, '1']]
                }]
            }
        })

  def query(self, name, body):
    del body
    m = re.match(r'projects/([^/]+)', name)
    project_id = m.group(1)
    return apis_stub.RestCallStub(project_id, 'monitoring-query')

  def query_next(self, previous_request, previous_response):
    del previous_request
    del previous_response
