""" Make REST API requests """
from typing import Any, Mapping, Optional, Protocol

import aiohttp


class Creds(Protocol):

  def get_token(self) -> str:
    pass


class API:
  """ Class abstracting aspects of REST API requests """

  def __init__(self, creds: Creds) -> None:
    self._creds = creds

  async def call(self,
                 method: str,
                 url: str,
                 json: Optional[Any] = None) -> Any:
    async with aiohttp.request(method,
                               url,
                               headers=self._get_headers(),
                               json=json) as resp:
      if resp.status != 200:
        raise RuntimeError(f'http status {resp.status} calling {method} {url}')
      return await resp.json()

  def _get_headers(self) -> Mapping[str, str]:
    return {'Authorization': f'Bearer {self._creds.get_token()}'}
