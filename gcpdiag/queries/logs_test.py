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
"""Test code in logs.py."""

import concurrent.futures
import re
import time
from unittest import mock

from gcpdiag import models
from gcpdiag.queries import apis_stub, logs, logs_stub

DUMMY_PROJECT_ID = 'gcpdiag-gke1-aaaa'
FIRST_INSERT_ID = '-tt9mudi768'


@mock.patch('gcpdiag.queries.apis.get_api', new=apis_stub.get_api_stub)
class TestLogs:
  """Test logs.py functions."""

  def test_single_query(self):
    context = models.Context(project_id=DUMMY_PROJECT_ID)
    query = logs.query(
        project_id=context.project_id,
        resource_type='gce_instance',
        log_name='fake.log',
        filter_str='filter1',
    )

    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
      logs.execute_queries(executor, context)
      # verify the number of entries
      all_entries = list(query.entries)
      assert len(all_entries) > 0
      # verify that the first log entry is correct (the earliest one)
      first = next(iter(query.entries))
      assert first['insertId'] == FIRST_INSERT_ID

  def test_aggregated_query(self):
    """Verify that multiple queries get aggregated into one."""
    context = models.Context(project_id=DUMMY_PROJECT_ID)
    logs.query(project_id=context.project_id,
               resource_type='gce_instance',
               log_name='fake.log',
               filter_str='filter1')
    logs.query(project_id=context.project_id,
               resource_type='gce_instance',
               log_name='fake.log',
               filter_str='filter2')
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
      logs.execute_queries(executor, context)
    # verify the filter that is used
    assert re.match(
        r'timestamp>"\d\d\d\d-\d\d-\d\dT\d\d:\d\d:\d\d\+00:00"\n'
        r'resource.type="gce_instance"\n'
        r'logName="fake.log"\n'
        r'\(\(filter1\) OR \(filter2\)\)', logs_stub.logging_body['filter'])
    # also verify other parameters of the job
    assert logs_stub.logging_body['orderBy'] == 'timestamp desc'
    assert logs_stub.logging_body['pageSize'] == 500
    assert logs_stub.logging_body['resourceNames'] == [
        'projects/gcpdiag-gke1-aaaa'
    ]

  def test_format_log_entry(self):
    with mock.patch.dict('os.environ', {'TZ': 'America/Los_Angeles'}):
      time.tzset()
      assert logs.format_log_entry({
          'jsonPayload': {
              'message': 'test message'
          },
          'receiveTimestamp': '2022-03-24T13:26:37.370862686Z'
      }) == '2022-03-24 06:26:37-07:00: test message'
      assert logs.format_log_entry({
          'jsonPayload': {
              'MESSAGE': 'test message'
          },
          'receiveTimestamp': '2022-03-24T13:26:37.370862686Z'
      }) == '2022-03-24 06:26:37-07:00: test message'
      assert logs.format_log_entry({
          'textPayload': 'test message',
          'receiveTimestamp': '2022-03-24T13:26:37.370862686Z'
      }) == '2022-03-24 06:26:37-07:00: test message'
