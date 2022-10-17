""" Make REST API requests """
from typing import Any, Dict, Iterable, Optional, Protocol

import aiohttp

from gcpdiag.queries import apis_utils


class Creds(Protocol):

  def update_headers(self, headers: Dict[str, str]) -> None:
    pass


class Sleeper(Protocol):

  async def sleep(self, seconds: float) -> None:
    pass


class RetryStrategy(Protocol):

  def get_sleep_intervals(self) -> Iterable[float]:
    pass


class API:
  """ Class abstracting aspects of REST API requests """

  def __init__(self, creds: Creds, retry_strategy: RetryStrategy,
               sleeper: Sleeper) -> None:
    self._creds = creds
    self._retry_strategy = retry_strategy
    self._sleeper = sleeper

  async def call(self,
                 method: str,
                 url: str,
                 json: Optional[Any] = None) -> Any:
    for timeout in self._retry_strategy.get_sleep_intervals():
      async with aiohttp.request(method,
                                 url,
                                 headers=self._get_headers(),
                                 json=json) as resp:
        if resp.status == 200:
          return await resp.json()
        if not apis_utils.should_retry(resp.status):
          raise RuntimeError(
              f'http status {resp.status} calling {method} {url}')
      await self._sleeper.sleep(timeout)
    raise RuntimeError('failed to get an API response')

  def _get_headers(self) -> Dict[str, str]:
    headers: Dict[str, str] = {}
    self._creds.update_headers(headers)
    return headers
