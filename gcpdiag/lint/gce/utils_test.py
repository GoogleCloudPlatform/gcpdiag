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
"""Test utility functions for GCE linters."""

from collections import deque
from unittest.mock import PropertyMock, patch

from gcpdiag import config, models
from gcpdiag.lint.gce.utils import SerialOutputSearch
from gcpdiag.queries import logs
from gcpdiag.queries.gce import SerialOutputQuery, SerialPortOutput


class TestUtils:
  """Test for GCE lint Util"""
  context = models.Context(project_id='x')
  cl_logs = [{
      'resource': {
          'labels': {
              'instance_id': '1'
          },
      },
      'textPayload': 'entry_one',
      'receiveTimestamp': '2022-03-24T13:26:37.370862686Z'
  }, {
      'resource': {
          'labels': {
              'instance_id': '1'
          },
      },
      'textPayload': 'entry_x',
      'receiveTimestamp': '2022-03-25T13:26:37.370862686Z'
  }]

  serial_logs: deque = deque()
  serial_logs.appendleft(SerialPortOutput('x', '1', ['entry_one', 'entry_x']))
  serial_logs.appendleft(SerialPortOutput('x', '2', ['entry_x', 'entry_two']))

  @patch.object(SerialOutputQuery,
                'entries',
                new_callable=PropertyMock,
                return_value=serial_logs)
  @patch.object(logs.LogsQuery,
                'entries',
                new_callable=PropertyMock,
                return_value=cl_logs)
  def test_query_order_with_buffer_enabled(self, mock_logs_query_entries,
                                           mock_serial_output_query_entries):

    # Test when customer has provided the `--enable_gce_serial_buffer` flag
    config.init({'enable_gce_serial_buffer': True}, 'x')
    search = SerialOutputSearch(context=self.context,
                                search_strings=['entry_one', 'entry_two'])
    entry = search.get_last_match('1')
    assert entry.text == 'entry_one'
    entry = search.get_last_match('2')
    assert entry.text == 'entry_two'
    assert entry.timestamp is None
    assert entry.timestamp_iso is None
    #instance doesn't have any serial output and not cloud logging entry
    entry = search.get_last_match('3')
    assert entry is None
    # When cloud logging doesn't have the entry direct outputs should be checked
    assert mock_logs_query_entries.called
    # Check that serial logs entries where check with the buffer enabled.
    assert mock_serial_output_query_entries.called

  # Patch the `entries()` method of `LogsQuery` and `SerialOutputQuery`.
  @patch.object(SerialOutputQuery,
                'entries',
                new_callable=PropertyMock,
                return_value=serial_logs)
  @patch.object(logs.LogsQuery,
                'entries',
                new_callable=PropertyMock,
                return_value=cl_logs)
  def test_query_order_buffer_disabled(self, mock_logs_query_entries,
                                       mock_serial_output_query_entries):
    # `--enable_gce_serial_buffer` not provided
    config.init({'enable_gce_serial_buffer': False}, 'x')
    search = SerialOutputSearch(context=self.context,
                                search_strings=['entry_one', 'entry_two'])
    search.query.entries = self.cl_logs
    # Check that serial logs are not fetched if the buffer is not enabled.
    # With the default config, `enable_gce_serial_buffer` is `False`.
    # There are logs in cloud logging so should use that
    entry = search.get_last_match('1')
    assert entry.text == 'entry_one'
    assert entry.timestamp == logs.log_entry_timestamp(self.cl_logs[0])

    entry = search.get_last_match('2')
    assert entry is None
    #instance doesn't have any serial output and not cloud logging entry
    entry = search.get_last_match('3')
    assert entry is None

    assert mock_logs_query_entries.called
    #serial entries should not be fetched.
    assert not mock_serial_output_query_entries.called


def test_is_serial_logs_available():
  config.init({'enable_gce_serial_buffer': False}, 'x')
