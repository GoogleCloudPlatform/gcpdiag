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

import concurrent.futures
import unittest
from unittest import mock

import googleapiclient.errors
import httplib2

from gcpdiag import config, models, utils
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
class Test(unittest.TestCase):

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

  @mock.patch('gcpdiag.queries.apis_utils.execute_single_request')
  @mock.patch('gcpdiag.executor.get_executor')
  def test_execute_concurrently_api_server(self, mock_get_executor,
                                           mock_execute_single_request):
    api = apis_stub.get_api_stub('compute', 'v1')
    context = models.Context(project_id='test-project')
    context.context_provider = mock.Mock()
    mock_executor = mock.Mock()
    mock_get_executor.return_value = mock_executor
    mock_execute_single_request.side_effect = [
        ({
            'items': ['a', 'b']
        }, None),
        ({
            'items': ['e']
        }, None),
    ]

    # Mock the submit method to return a Future object
    def mock_submit(fn, *args, **kwargs):
      future = concurrent.futures.Future()
      try:
        result = fn(*args, **kwargs)
        future.set_result(result)
      except googleapiclient.errors.HttpError as e:
        future.set_exception(e)
      return future

    mock_executor.submit.side_effect = mock_submit

    requests = [RequestMock(1), RequestMock(3)]
    results = list(apis_utils.execute_concurrently(api, requests, context))

    mock_get_executor.assert_called_once_with(context)
    self.assertEqual(mock_executor.submit.call_count, 2)
    self.assertEqual(len(results), 2)
    # Check that first result element is request
    self.assertIsInstance(results[0][0], RequestMock)
    self.assertIsInstance(results[1][0], RequestMock)
    self.assertEqual(sorted(r[0].n for r in results), [1, 3])

  @mock.patch('gcpdiag.queries.apis_utils.batch_execute_all')
  def test_execute_concurrently_cli(self, mock_batch_execute_all):
    api = apis_stub.get_api_stub('compute', 'v1')
    context = models.Context(project_id='test-project')
    mock_batch_execute_all.return_value = iter([
        (RequestMock(1), {
            'items': ['a', 'b']
        }, None),
        (RequestMock(3), {
            'items': ['e']
        }, None),
    ])

    requests = [RequestMock(1), RequestMock(3)]
    results = list(apis_utils.execute_concurrently(api, requests, context))

    mock_batch_execute_all.assert_called_once_with(api, requests)
    assert len(results) == 2


class ExecuteConcurrentlyWithPaginationTest(unittest.TestCase):
  """Tests for execute_concurrently_with_pagination."""

  def setUp(self):
    super().setUp()
    self.mock_api = mock.Mock()
    self.request_1 = mock.Mock()
    self.request_1.uri = 'request/1'
    self.request_2 = mock.Mock()
    self.request_2.uri = 'request/2'

  @mock.patch('gcpdiag.queries.apis_utils.batch_list_all')
  def test_cli_context_uses_batch_list_all(self, mock_batch_list_all):
    """Verify that batch_list_all is called in CLI context."""
    context = models.Context(project_id='test-project')
    requests = [self.request_1]
    mock_batch_list_all.return_value = iter(['item1', 'item2'])

    results = list(
        apis_utils.execute_concurrently_with_pagination(
            self.mock_api,
            requests,
            next_function_mock,
            context,
            log_text='testing',
            response_keyword='items'))

    self.assertEqual(results, ['item1', 'item2'])
    mock_batch_list_all.assert_called_once_with(self.mock_api, requests,
                                                next_function_mock, 'testing',
                                                'items')

  @mock.patch('gcpdiag.queries.apis_utils.execute_concurrently')
  def test_api_context_single_page(self, mock_execute_concurrently):
    """Test API context with a single page of results."""
    context = models.Context(project_id='test-project', context_provider='api')
    requests = [self.request_1]
    # execute_concurrently yields: (request, response, exception)
    mock_execute_concurrently.return_value = iter([
        (self.request_1, {
            'items': ['item1']
        }, None),
    ])

    results = list(
        apis_utils.execute_concurrently_with_pagination(
            self.mock_api,
            requests,
            mock.Mock(),
            context,
            log_text='testing',
            response_keyword='items'))

    self.assertEqual(results, ['item1'])
    mock_execute_concurrently.assert_called_once()

  @mock.patch('gcpdiag.queries.apis_utils.execute_concurrently')
  def test_api_context_multi_page(self, mock_execute_concurrently):
    """Test API context with multiple pages of results."""
    context = models.Context(project_id='test-project', context_provider='api')
    req1, resp1 = mock.Mock(uri='uri1'), {
        'items': ['item1'],
        'nextPageToken': 'page2'
    }
    req2, resp2 = mock.Mock(uri='uri2'), {'items': ['item2']}

    def side_effect_func(*args, **kwargs):  # pylint: disable=unused-argument
      if req1 in kwargs['requests']:
        return iter([(req1, resp1, None)])
      elif req2 in kwargs['requests']:
        return iter([(req2, resp2, None)])
      return iter([])

    mock_execute_concurrently.side_effect = side_effect_func

    def next_func(previous_request, previous_response):  # pylint: disable=unused-argument
      if previous_response.get('nextPageToken') == 'page2':
        return req2
      return None

    results = list(
        apis_utils.execute_concurrently_with_pagination(
            self.mock_api, [req1],
            next_func,
            context,
            log_text='testing',
            response_keyword='items'))

    self.assertEqual(results, ['item1', 'item2'])
    self.assertEqual(mock_execute_concurrently.call_count, 2)

  @mock.patch('gcpdiag.queries.apis_utils.execute_concurrently')
  def test_api_context_skips_404(self, mock_execute_concurrently):
    """Test that 404 errors are skipped in API context."""
    context = models.Context(project_id='test-project', context_provider='api')
    requests = [self.request_1]
    http_error_404 = googleapiclient.errors.HttpError(resp=httplib2.Response(
        {'status': 404}),
                                                      content=b'Not Found')
    mock_execute_concurrently.return_value = iter([
        (self.request_1, None, http_error_404),
    ])

    results = list(
        apis_utils.execute_concurrently_with_pagination(
            self.mock_api,
            requests,
            mock.Mock(),
            context,
            log_text='testing',
            response_keyword='items'))

    self.assertEqual(results, [])
    mock_execute_concurrently.assert_called_once()

  @mock.patch('gcpdiag.queries.apis_utils.execute_concurrently')
  def test_api_context_raises_other_error(self, mock_execute_concurrently):
    """Test that non-404 errors raise GcpApiError in API context."""
    context = models.Context(project_id='test-project', context_provider='api')
    requests = [self.request_1]
    http_error_500 = googleapiclient.errors.HttpError(resp=httplib2.Response(
        {'status': 500}),
                                                      content=b'Server Error')
    mock_execute_concurrently.return_value = iter([
        (self.request_1, None, http_error_500),
    ])

    with self.assertRaises(utils.GcpApiError):
      list(
          apis_utils.execute_concurrently_with_pagination(
              self.mock_api,
              requests,
              mock.Mock(),
              context,
              log_text='testing',
              response_keyword='items'))
