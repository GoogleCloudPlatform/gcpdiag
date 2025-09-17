# Copyright 2021 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""ThreadPoolExecutor instance that can be used to run tasks in parallel"""

import concurrent.futures
from typing import Any, Callable, Iterable, Optional

from gcpdiag import config, models

_real_executor: Optional[concurrent.futures.ThreadPoolExecutor] = None


def _get_real_executor() -> concurrent.futures.ThreadPoolExecutor:
  global _real_executor
  if _real_executor is None:
    _real_executor = concurrent.futures.ThreadPoolExecutor(
        max_workers=config.MAX_WORKERS)
  return _real_executor


def _context_wrapper(fn, context: models.Context):

  def wrapped(*args, **kwargs):
    provider = context.context_provider
    if provider:
      provider.setup_thread_context()
    try:
      return fn(*args, **kwargs)
    finally:
      if provider:
        provider.teardown_thread_context()

  return wrapped


class ContextAwareExecutor:
  """A ThreadPoolExecutor wrapper that propagates the gcpdiag context.

  This executor ensures that the thread-local context (e.g., for API clients)
  is properly set up and torn down for each task executed in the thread pool.
  """

  def __init__(self, context: models.Context):
    self._context = context
    self._executor = _get_real_executor()

  def submit(self, fn: Callable[..., Any], *args: Any,
             **kwargs: Any) -> concurrent.futures.Future[Any]:
    wrapped_fn = _context_wrapper(fn, self._context)
    return self._executor.submit(wrapped_fn, *args, **kwargs)

  def map(
      self,
      fn: Callable[..., Any],
      *iterables: Iterable[Any],
      timeout: Optional[float] = None,
      chunksize: int = 1,
  ):
    wrapped_fn = _context_wrapper(fn, self._context)
    return self._executor.map(wrapped_fn,
                              *iterables,
                              timeout=timeout,
                              chunksize=chunksize)

  def shutdown(self, wait: bool = True):
    # We don't shut down the underlying global executor here
    pass

  def __enter__(self):
    return self

  def __exit__(self, exc_type, exc_val, exc_tb):
    self.shutdown(wait=True)


def get_executor(context: models.Context) -> ContextAwareExecutor:
  return ContextAwareExecutor(context)
