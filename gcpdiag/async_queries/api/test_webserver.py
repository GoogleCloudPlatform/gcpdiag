""" Simple web server used for testing """
from typing import Any, List, Protocol

from aiohttp import web


class Response(Protocol):

  def get_response(self) -> Any:
    pass


class Success:
  """ Canned successful response """

  def __init__(self, data: Any) -> None:
    self.data = data

  def get_response(self) -> Any:
    return web.json_response(self.data)


AIOHTTP_EXCEPTIONS_BY_CODE = {
    408: web.HTTPRequestTimeout,
    429: web.HTTPTooManyRequests,
    500: web.HTTPInternalServerError
}


class Failure:
  """ Canned failed response """
  _status: int

  def __init__(self, status: int = 500) -> None:
    self._status = status

  def get_response(self) -> Any:
    assert self._status in AIOHTTP_EXCEPTIONS_BY_CODE
    # aiohttp uses a separate exception for every HTTP status code
    # https://docs.aiohttp.org/en/latest/web_exceptions.html
    # you might need to add another exception if you want to use a
    # new status code
    raise AIOHTTP_EXCEPTIONS_BY_CODE[self._status]()


class WebServer:
  """ Simple web server used for testing """

  responses: List[Response]

  def __init__(self, port: int, expected_auth_token: str) -> None:
    self.port = port
    self.responses = []
    self.expected_auth_token = expected_auth_token

  async def start(self) -> None:
    routes = web.RouteTableDef()

    @routes.get('/test')
    # pylint: disable=unused-argument
    async def hello(request: Any) -> Any:
      assert len(self.responses) > 0
      assert request.headers[
          'test_auth'] == f'test_auth {self.expected_auth_token}'
      return self.responses.pop(0).get_response()

    app = web.Application()
    app.add_routes(routes)

    self.runner = web.AppRunner(app)
    await self.runner.setup()
    site = web.TCPSite(self.runner, 'localhost', self.port)
    await site.start()

  async def stop(self) -> None:
    await self.runner.cleanup()
