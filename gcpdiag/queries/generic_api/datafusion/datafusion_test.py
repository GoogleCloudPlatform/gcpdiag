"""
  Tests for datafusion API
  python -m unittest gcpdiag.generic_api.datafusion.datafusion_test
"""

import unittest
from typing import Dict
from unittest.mock import Mock, patch

import requests

from gcpdiag.async_queries.api import constant_time_retry_strategy
from gcpdiag.queries.generic_api.datafusion import datafusion


class FakeCreds:
  _token: str

  def __init__(self, token: str) -> None:
    self._token = token

  def update_headers(self, headers: Dict[str, str]) -> None:
    headers['test_auth'] = f'test_auth {self._token}'


class TestDatafusion(unittest.TestCase):
  """ Tests for API call """

  def setUp(self):
    self._token = 'fake token'
    self._base_url = 'https://datafusion.googleusercontent.com'
    self._api = datafusion.Datafusion(
        self._base_url,
        creds=FakeCreds(self._token),
        retry_strategy=constant_time_retry_strategy.
        ConstantTimeoutRetryStrategy(timeout=42, retries=3))

  @patch('requests.request')
  def test_get_system_profiles_success(self, mock_request):
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {'profile': {}}
    mock_request.return_value = mock_response

    response = self._api.get_system_profiles()
    self.assertEqual(response, {'profile': {}})

    mock_request.assert_called_once_with(
        'GET',
        f'{self._base_url}/v3/profiles',
        headers={'test_auth': f'test_auth {self._token}'},
        params=None)
    mock_response.json.assert_called_once()

  @patch('requests.request')
  def test_get_all_namespaces(self, mock_request):
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {'namespaces': []}
    mock_request.return_value = mock_response

    response = self._api.get_all_namespaces()
    self.assertEqual(response, {'namespaces': []})

    mock_request.assert_called_once_with(
        'GET',
        f'{self._base_url}/v3/namespaces',
        headers={'test_auth': f'test_auth {self._token}'},
        params=None)
    mock_response.json.assert_called_once()

  @patch('requests.request')
  def test_get_user_profiles(self, mock_request):
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {'userProfiles': []}
    mock_request.return_value = mock_response

    response = self._api.get_user_profiles(namespace='test-namespace')
    self.assertEqual(response, {'userProfiles': []})

    mock_request.assert_called_once_with(
        'GET',
        f'{self._base_url}/v3/namespaces/test-namespace/profiles',
        headers={'test_auth': f'test_auth {self._token}'},
        params=None)
    mock_response.json.assert_called_once()

  @patch('requests.request')
  def test_get_system_profiles_failure(self, mock_request):
    mock_request.side_effect = requests.exceptions.RequestException(
        'Network error')

    with patch.object(constant_time_retry_strategy.ConstantTimeoutRetryStrategy,
                      'get_sleep_intervals',
                      return_value=[0.1, 0.2, 0.3]):
      with self.assertRaises(RuntimeError) as context:
        self._api.get('test_endpoint')

    self.assertIn('Failed to get an API response after maximum retries',
                  str(context.exception))
    self.assertEqual(mock_request.call_count, 3)

  @patch('requests.request')
  def test_get_user_profiles_temporary_failure_then_success(self, mock_request):
    temporary_failure = Mock()
    temporary_failure.status_code = 500
    temporary_failure.text = 'Internal Server Error'

    sucessful_response = Mock()
    sucessful_response.status_code = 200
    sucessful_response.json.return_value = {'userProfiles': []}

    mock_request.side_effect = [
        temporary_failure, temporary_failure, sucessful_response
    ]
    with patch.object(constant_time_retry_strategy.ConstantTimeoutRetryStrategy,
                      'get_sleep_intervals',
                      return_value=[0.1, 0.2, 0.3]):
      response = self._api.get_user_profiles(namespace='test-namespace')

    self.assertEqual(response, {'userProfiles': []})
    self.assertEqual(mock_request.call_count, 3)

  @patch('requests.request')
  def test_get_all_namespaces_max_retries_exceeded(self, mock_request):
    mock_response = Mock()
    mock_response.status_code = 500
    mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError(
        'Internal Server Error')
    mock_request.return_value = mock_response

    with patch.object(constant_time_retry_strategy.ConstantTimeoutRetryStrategy,
                      'get_sleep_intervals',
                      return_value=[0.1, 0.2, 0.3]):
      with self.assertRaises(RuntimeError) as context:
        self._api.get_all_namespaces()

    self.assertIn('Failed to get an API response after maximum retries',
                  str(context.exception))
    self.assertEqual(mock_request.call_count, 3)

  @patch('requests.request')
  def test_get_user_profiles_failure(self, mock_request):
    mock_response = Mock()
    mock_response.status_code = 404
    mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError(
        'Not Found')
    mock_request.return_value = mock_response

    with self.assertRaises(RuntimeError) as context:
      self._api.get_user_profiles(namespace='test-namespace')

    self.assertIn(
        'http status 404 calling GET https://datafusion.googleusercontent.com/v3/namespaces/test-namespace/profiles',  # pylint: disable=line-too-long
        str(context.exception))
    self.assertEqual(mock_request.call_count, 1)
