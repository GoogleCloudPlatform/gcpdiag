""" Common protocols used by async queries """

from typing import Any, Iterable, Optional, Protocol


class API(Protocol):

  async def call(self,
                 method: str,
                 url: str,
                 json: Optional[Any] = None) -> Any:
    pass


class ProjectRegions(Protocol):

  async def get_all(self) -> Iterable[str]:
    pass
