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
"""Test code in apis_utils.py."""

from unittest import mock

from gcpdiag import config, utils
from gcpdiag.queries import apis_stub, apis_utils


class RequestMock(apis_stub.ApiStub):
  """Mock a googleapiclient.request object."""

  def __init__(self,
               n: int,
               fail_count: int = 0,
               fail_status: int = 429,
               uri: str = 'googleapis.com'):
    self.n = n
    if fail_count:
      self.fail_next(fail_count, fail_status)
    self.uri = uri

  def execute(self, num_retries: int = 0):
    del num_retries
    self._maybe_raise_api_exception()
    if self.n == 1:
      return {'items': ['a', 'b']}
    elif self.n == 2:
      return {'items': ['c', 'd']}
    elif self.n == 3:
      return {'items': ['e']}


def next_function_mock(previous_request, previous_response):
  del previous_response
  if previous_request.n == 1:
    return RequestMock(2)
  else:
    return None


mock_sleep_slept_time = []


def mock_sleep(sleep_time: float):
  mock_sleep_slept_time.append(sleep_time)


@mock.patch('gcpdiag.queries.apis.get_api', new=apis_stub.get_api_stub)
@mock.patch('time.sleep', new=mock_sleep)
class Test:

  def test_list_all(self):
    results = list(apis_utils.list_all(RequestMock(1), next_function_mock))
    assert (results == ['a', 'b', 'c', 'd'])

  def test_multi_list_all(self):
    results = list(
        apis_utils.multi_list_all(requests=[RequestMock(1),
                                            RequestMock(3)],
                                  next_function=next_function_mock))
    assert (results == ['a', 'b', 'c', 'd', 'e'])

  def test_batch_list_all(self):
    api = apis_stub.get_api_stub('compute', 'v1')
    results = list(
        apis_utils.batch_list_all(  #
            api=api,
            requests=[RequestMock(1), RequestMock(3)],
            next_function=next_function_mock,
            log_text='testing'))
    # batch_list_all will first retrieve all requests (first page), then in a
    # second step any further required pages.
    assert (results == ['a', 'b', 'e', 'c', 'd'])

  def test_batch_execute_all(self):
    api = apis_stub.get_api_stub('compute', 'v1')
    results = list(
        apis_utils.batch_execute_all(
            api, [RequestMock(1), RequestMock(3)]))
    # requests
    assert [x[0].n for x in results] == [1, 3]
    # responses
    assert [x[1] for x in results] == [{'items': ['a', 'b']}, {'items': ['e']}]

  def test_batch_execute_all_unretriable_exception(self):
    api = apis_stub.get_api_stub('compute', 'v1')
    results = list(
        apis_utils.batch_execute_all(
            api,
            [RequestMock(1, fail_count=1, fail_status=403),
             RequestMock(3)]))
    assert isinstance(results[0][2], utils.GcpApiError) and \
        results[0][2].status == 403

  def test_batch_execute_all_too_many_failures(self):
    api = apis_stub.get_api_stub('compute', 'v1')
    results = list(
        apis_utils.batch_execute_all(api, [
            RequestMock(1, fail_count=config.API_RETRIES + 1, fail_status=429),
            RequestMock(3)
        ]))
    assert isinstance(results[1][2], Exception)

  def test_batch_execute_all_retriable_exception(self):
    global mock_sleep_slept_time
    mock_sleep_slept_time = []
    api = apis_stub.get_api_stub('compute', 'v1')
    results = list(
        apis_utils.batch_execute_all(api, [
            RequestMock(1, fail_count=config.API_RETRIES, fail_status=429),
            RequestMock(3)
        ]))
    assert len(mock_sleep_slept_time) == config.API_RETRIES
    # 20% is random, progression: 1, 1.4, 2.0, 2.7, ... 28.9 (10 retries)
    assert 0.8 <= mock_sleep_slept_time[0] <= 1.0
    assert 1.1 <= mock_sleep_slept_time[1] <= 1.4
    # requests
    assert [x[0].n for x in results] == [3, 1]
    # responses
    assert [x[1] for x in results] == [{'items': ['e']}, {'items': ['a', 'b']}]

  def test_batch_execute_batchapi_tempfail(self):
    """Test the batch API producing a retryable failure."""
    global mock_sleep_slept_time
    mock_sleep_slept_time = []
    api = apis_stub.get_api_stub('compute', 'v1')
    api.fail_next(1)
    results = list(
        apis_utils.batch_execute_all(
            api, [RequestMock(1), RequestMock(3)]))
    assert len(mock_sleep_slept_time) == 1
    # requests
    assert [x[0].n for x in results] == [1, 3]
    # responses
    assert [x[1] for x in results] == [{'items': ['a', 'b']}, {'items': ['e']}]
