'Testing double for gcpdiag.async_queries.api.API'
from asyncio import sleep
from typing import Any, List, Optional, Tuple


class APICall:
  'Helper class representing an API call'
  method: str
  url: str
  json: Any

  def __init__(self, method: str, url: str, json: Any = None) -> None:
    self.method = method
    self.url = url
    self.json = json

  def __eq__(self, other: Any) -> bool:
    assert isinstance(other, APICall)
    return self.method == other.method and self.url == other.url and self.json == other.json

  def __repr__(self) -> str:
    return f'<Call: {self.method} {self.url} {self.json}>'


class FakeAPI:
  'Testing double for gcpdiag.async_queries.api.API'
  responses: List[Tuple[APICall, Any]]
  calls: List[APICall]

  def __init__(self, responses: List[Tuple[APICall, Any]]) -> None:
    self.responses = responses
    self.calls = []

  async def call(self,
                 method: str,
                 url: str,
                 json: Optional[Any] = None) -> Any:
    call = APICall(method, url, json)
    await sleep(0)
    self.calls.append(call)
    return self.get_response(call)

  def get_response(self, call: APICall) -> Any:
    for c, r in self.responses:
      if c == call:
        return r
    raise RuntimeError(f'Canned response not found for {call}')

  def count_calls(self, call: APICall) -> int:
    count = 0
    for c in self.calls:
      if c == call:
        count += 1
    return count
