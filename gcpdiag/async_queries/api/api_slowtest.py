"""
  Tests for API
  python -m unittest gcpdiag.async_queries.api_test
"""
import asyncio
import os
import unittest
from typing import Dict, List

from gcpdiag.async_queries.api import (api, constant_time_retry_strategy,
                                       test_webserver)


class FakeCreds:
  _token: str

  def __init__(self, token: str) -> None:
    self._token = token

  def update_headers(self, headers: Dict[str, str]) -> None:
    headers['test_auth'] = f'test_auth {self._token}'


class FakeSleeper:
  slept: List[float]

  def __init__(self) -> None:
    self.slept = []

  async def sleep(self, seconds: float) -> None:
    await asyncio.sleep(0)
    self.slept.append(seconds)


class TestAPI(unittest.IsolatedAsyncioTestCase):
  """ Tests for async API """

  async def asyncSetUp(self) -> None:
    self._token = 'fake token'
    self._port = int(os.environ['GCPDIAG_TEST_ASYNC_API_PORT'])

    self._server = test_webserver.WebServer(port=self._port,
                                            expected_auth_token=self._token)
    self._sleeper = FakeSleeper()
    self._api = api.API(creds=FakeCreds(self._token),
                        sleeper=self._sleeper,
                        retry_strategy=constant_time_retry_strategy.
                        ConstantTimeoutRetryStrategy(timeout=42, retries=3))
    await self._server.start()

  async def asyncTearDown(self) -> None:
    await self._server.stop()

  async def test_get_response(self) -> None:
    self._server.responses = [test_webserver.Success({'hello': 'world'})]
    result = await self._api.call(method='GET',
                                  url=f'http://localhost:{self._port}/test')
    self.assertEqual(result, {'hello': 'world'})

  async def test_enough_retries(self) -> None:
    self._server.responses = [
        test_webserver.Failure(),
        test_webserver.Failure(),
        test_webserver.Success({'hello': 'world'})
    ]
    result = await self._api.call(method='GET',
                                  url=f'http://localhost:{self._port}/test')
    self.assertEqual(result, {'hello': 'world'})
    self.assertListEqual(self._sleeper.slept, [42, 42])

  async def test_not_enough_retries(self) -> None:
    self._server.responses = [
        test_webserver.Failure(),
        test_webserver.Failure(),
        test_webserver.Failure(),
        test_webserver.Success({'hello': 'world'})
    ]
    with self.assertRaises(RuntimeError):
      await self._api.call(method='GET',
                           url=f'http://localhost:{self._port}/test')
    self.assertListEqual(self._sleeper.slept, [42, 42, 42])

  async def test_http_429_retried(self) -> None:
    self._server.responses = [
        test_webserver.Failure(429),
        test_webserver.Failure(429),
        test_webserver.Success({'hello': 'world'})
    ]
    result = await self._api.call(method='GET',
                                  url=f'http://localhost:{self._port}/test')
    self.assertEqual(result, {'hello': 'world'})
    self.assertListEqual(self._sleeper.slept, [42, 42])

  async def test_other_4xx_http_not_retried(self) -> None:
    self._server.responses = [
        test_webserver.Failure(408),
        test_webserver.Failure(408),
        test_webserver.Success({'hello': 'world'})
    ]
    with self.assertRaises(RuntimeError):
      await self._api.call(method='GET',
                           url=f'http://localhost:{self._port}/test')
    self.assertListEqual(self._sleeper.slept, [])
