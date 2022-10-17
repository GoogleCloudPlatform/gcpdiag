""" Retry strategy: n retries with fixed timeout between them """
from typing import Iterator


class ConstantTimeoutRetryStrategy:
  """ Retry strategy: n retries with fixed timeout between them """

  _retries: int
  _timeout: int

  def __init__(self, retries: int, timeout: int) -> None:
    self._retries = retries
    self._timeout = timeout

  def get_sleep_intervals(self) -> Iterator[float]:
    for _ in range(self._retries):
      yield self._timeout
