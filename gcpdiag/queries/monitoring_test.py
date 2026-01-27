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
"""Test code in monitoring.py."""

from datetime import datetime, timedelta
from unittest import mock

from gcpdiag.queries import apis_stub, monitoring

DUMMY_PROJECT_NAME = 'gcpdiag-gce1-aaaa'
DUMMY_INSTANCE_NAME = 'gce1'
DUMMY_ZONE = 'europe-west4-a'


@mock.patch('gcpdiag.queries.apis.get_api', new=apis_stub.get_api_stub)
class Test:

  def test_timeserie(self):
    ts_col = monitoring.query(DUMMY_PROJECT_NAME,
                              'mocked query (this is ignored)')
    fs = frozenset({
        f'resource.zone:{DUMMY_ZONE}',
        f'metric.instance_name:{DUMMY_INSTANCE_NAME}'
    })
    assert fs in ts_col.keys()
    value = ts_col[fs]

    # expected data:
    # {
    #   'labels': {
    #     'resource.zone': 'europe-west4-a',
    #     'metric.instance_name': 'gce1'
    #   },
    #   'start_time': '2021-05-19T15:40:31.414435Z',
    #   'end_time': '2021-05-19T15:45:31.414435Z',
    #   'values': [[10917.0, 5], [11187.0, 4]]
    # }
    assert value['labels']['metric.instance_name'] == 'gce1'
    assert 'start_time' in value
    assert 'end_time' in value
    assert isinstance(value['values'][0][0], float)
    assert isinstance(value['values'][1][0], float)
    assert isinstance(value['values'][0][1], int)
    assert isinstance(value['values'][1][1], int)

  def test_queryrange(self):
    end_time = datetime.now()
    start_time = end_time - timedelta(minutes=30)
    vpn_query = 'cloud_monitoring_vpn_gateway_network_googleapis_com_vpn_gateway_tunnel_is_up'
    response = monitoring.queryrange(project_id=DUMMY_PROJECT_NAME,
                                     query_str=vpn_query,
                                     start_time=start_time,
                                     end_time=end_time)
    assert response['status'] == 'success'
    results = response['data']['result']
    if len(results) > 0:
      metric_labels = results[0]['metric']
      assert 'project_id' in metric_labels
