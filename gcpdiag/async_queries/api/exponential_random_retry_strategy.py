"""
  Retry strategy:
    n retries with exponential timeout plus some random deviations
"""
from typing import Iterator, Protocol

from gcpdiag.queries import apis_utils


class Random(Protocol):

  def generate(self) -> float:
    pass


class ExponentialRandomTimeoutRetryStrategy:
  """
    Retry strategy:
      n retries with exponential timeout plus some random deviations
  """

  _retries: int
  _random_pct: float
  _multiplier: float
  _random: Random

  def __init__(self, retries: int, random_pct: float, multiplier: float,
               random: Random) -> None:
    self._retries = retries
    self._random_pct = random_pct
    self._multiplier = multiplier
    self._random = random

  def get_sleep_intervals(self) -> Iterator[float]:
    for i in range(self._retries):
      yield apis_utils.get_nth_exponential_random_retry(
          n=i,
          random_pct=self._random_pct,
          multiplier=self._multiplier,
          random_fn=self._random.generate)
