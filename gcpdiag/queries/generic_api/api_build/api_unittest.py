"""
  Tests for API
  python -m unittest gcpdiag.queries.generic_api.api_build.api_unittest
"""

import unittest
from typing import Dict
from unittest.mock import Mock, patch

from gcpdiag.async_queries.api import constant_time_retry_strategy
from gcpdiag.queries.generic_api.api_build import api


class FakeCreds:
  _token: str

  def __init__(self, token: str) -> None:
    self._token = token

  def update_headers(self, headers: Dict[str, str]) -> None:
    headers['test_auth'] = f'test_auth {self._token}'


class TestAPI(unittest.TestCase):
  """ Tests for API call """

  def setUp(self):
    self._token = 'fake token'
    self._base_url = 'https://test.com'
    self._api = api.API(self._base_url,
                        creds=FakeCreds(self._token),
                        retry_strategy=constant_time_retry_strategy.
                        ConstantTimeoutRetryStrategy(timeout=42, retries=3))

  @patch('requests.request')
  def test_sucessful_get_request(self, mock_request):
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {'hello': 'world'}
    mock_request.return_value = mock_response
    response = self._api.get('test_endpoint')
    self.assertEqual(response, {'hello': 'world'})

    mock_request.assert_called_once_with(
        'GET',
        f'{self._base_url}/test_endpoint',
        headers={'test_auth': f'test_auth {self._token}'},
        params=None)
    mock_response.json.assert_called_once()

  @patch('requests.request')
  def test_failure_get_request(self, mock_request):
    mock_response = Mock()
    mock_response.status_code = 404
    mock_response.text = 'Not found'
    mock_request.return_value = mock_response

    with self.assertRaises(RuntimeError) as context:
      self._api.get('test_endpoint')

    self.assertIn('http status 404 calling GET https://test.com/test_endpoint',
                  str(context.exception))

  @patch('requests.request')
  def test_max_retries_exceeded(self, mock_request):
    mock_response = Mock()
    mock_response.status_code = 500
    mock_response.text = 'Internal Server Error'
    mock_request.return_value = mock_response

    with patch.object(constant_time_retry_strategy.ConstantTimeoutRetryStrategy,
                      'get_sleep_intervals',
                      return_value=[0.1, 0.2, 0.3]):
      with self.assertRaises(RuntimeError) as context:
        self._api.get('test_endpoint')

    self.assertIn('Failed to get an API response after maximum retries',
                  str(context.exception))
    self.assertEqual(mock_request.call_count, 3)

  @patch('requests.request')
  def test_temporary_failure_then_success(self, mock_request):
    temporary_failure = Mock()
    temporary_failure.status_code = 500
    temporary_failure.text = 'Internal Server Error'

    sucessful_response = Mock()
    sucessful_response.status_code = 200
    sucessful_response.json.return_value = {'hello': 'world'}

    mock_request.side_effect = [
        temporary_failure, temporary_failure, sucessful_response
    ]
    with patch.object(constant_time_retry_strategy.ConstantTimeoutRetryStrategy,
                      'get_sleep_intervals',
                      return_value=[0.1, 0.2, 0.3]):
      response = self._api.get('test_endpoint')

    self.assertEqual(response, {'hello': 'world'})
    self.assertEqual(mock_request.call_count, 3)
