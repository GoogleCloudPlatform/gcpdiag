"""
  Helper class to optimise gateway objects loading
  so that data only loaded once
"""
import asyncio
from typing import Callable, Coroutine, Optional


class Loader:
  """
    Helper class to optimise gateway objects loading
    so that data only loaded once

    Initialised with coroutine (async method) that should be run only once
    All clients are expected to await ensure_loaded method

    class MyGateway:
      def __init__(self):
        self.loader = Loader(self.load)
        ...

      async def get_response(self):
        await self.loader.ensure_loaded()
        return self.api_response

      async def load(self) -> None:
        ...
        self.api_response = await expensive_api_call()
        ...

    my_gateway = MyGateway()

    In this case, it doesn't matter how many clients call
    my_gateway.get_response() concurrently, expensive_api_call() only executed
    once (and all clients recive results of this call)
  """
  _load_task: Optional[asyncio.Task]
  _load_coroutine: Optional[Callable[[], Coroutine]]

  def __init__(self, load_coroutine: Callable[[], Coroutine]) -> None:
    self._load_coroutine = load_coroutine
    self._load_task = None

  async def ensure_loaded(self) -> None:
    assert self._load_coroutine is not None
    if self._load_task is None:
      self._load_task = asyncio.create_task(self._load_coroutine())
    await self._load_task
