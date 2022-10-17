""" Tests for ExponentialRandomTimeoutRetryStrategy """

from typing import List

import pytest

from gcpdiag.async_queries.api import exponential_random_retry_strategy


class FakeRandom:
  """ Test double for random numbers generator """
  _numbers: List[float]

  def __init__(self, numbers: List[float]) -> None:
    self._numbers = numbers

  def generate(self) -> float:
    return self._numbers.pop(0)


def test_retries() -> None:
  strategy = exponential_random_retry_strategy.ExponentialRandomTimeoutRetryStrategy(
      retries=5,
      random_pct=0.2,
      multiplier=1.4,
      random=FakeRandom([0.1, 0.2, 0.3, 0.4, 0.5]))
  # floats should be compared with some allowed error
  assert list(strategy.get_sleep_intervals()) == pytest.approx(
      [0.98, 1.344, 1.842, 2.524, 3.457], 0.001)
