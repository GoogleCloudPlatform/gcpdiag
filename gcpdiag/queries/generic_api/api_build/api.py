"""Make REST API requests."""

import time
from typing import Dict, Iterable, Protocol

import requests

from gcpdiag.queries import apis_utils


class Creds(Protocol):

  def update_headers(self, headers: Dict[str, str]) -> None:
    pass


class RetryStrategy(Protocol):

  def get_sleep_intervals(self) -> Iterable[float]:
    pass


class API:
  """Class abstracting aspects of REST API requests."""

  def __init__(self, base_url: str, creds: Creds,
               retry_strategy: RetryStrategy) -> None:
    self._creds = creds
    self._url = base_url
    self._retry_strategy = retry_strategy

  def _request(self, method: str, endpoint: str, **kwargs):
    for timeout in self._retry_strategy.get_sleep_intervals():
      try:
        url = f'{self._url}/{endpoint}'
        response = requests.request(method,
                                    url,
                                    headers=self._get_headers(),
                                    **kwargs)
        if response.status_code == 200:
          return response.json() if response.content else None
        if not apis_utils.should_retry(response.status_code):
          raise RuntimeError(
              f'http status {response.status_code} calling {method} {url}')
      except requests.exceptions.RequestException:
        time.sleep(timeout)
    raise RuntimeError('Failed to get an API response after maximum retries')

  def _get_headers(self) -> Dict[str, str]:
    headers: Dict[str, str] = {}
    self._creds.update_headers(headers)
    return headers

  def get(self, endpoint, params=None):
    return self._request('GET', endpoint, params=params)
