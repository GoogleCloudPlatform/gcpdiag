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

# Lint as: python3
"""Persistent caching using diskcache."""

import atexit
import collections
import contextlib
import functools
import hashlib
import logging
import pickle
import shutil
import tempfile
import threading
from typing import List

import diskcache
import googleapiclient.http

from gcpdiag import config

_cache = None
_bypass_cache = False
_use_cache = True


def _set_bypass_cache(value: bool):
  """Sets the cache bypass flag for the current thread.
  Only set this for code that need to re-fetch fresh data
  regardless or expiry and state of cached data.
  """
  thread = threading.current_thread()
  setattr(thread, '_bypass_cache', value)


def _get_bypass_cache():
  """Gets the cache bypass flag for the current thread. By default should always use cache"""
  # if cache is permanently disabled always bypass cache
  if not _use_cache:
    return False
  return getattr(threading.current_thread(), '_bypass_cache', False)


def configure_global_cache(enabled: bool):
  """ Used to enable or disable the use of caching in the application."""
  global _use_cache
  _use_cache = enabled


@contextlib.contextmanager
def bypass_cache():
  """
  A thread-safe context manager to temporarily set the cache bypass to True
  for the current thread, ensuring it is reverted back when the context exits.
  """
  original_value = _get_bypass_cache()
  _set_bypass_cache(True)
  try:
    yield
  finally:
    _set_bypass_cache(original_value)


def _clean_cache():
  """Remove all cached items with tag 'tmp'.

  We use 'tmp' to store data that should be cached only during a single
  execution of the script.
  """
  if _cache:
    count = _cache.evict('tmp')
    count += _cache.expire()
    if count:
      logging.debug('removed %d items from cache', count)


def _close_cache():
  if _cache:
    _clean_cache()
    _cache.close()


def get_disk_cache() -> diskcache.Cache:
  """Get a Diskcache.Cache object that can be used to cache data."""
  global _cache
  if _use_cache and not _cache:
    _cache = diskcache.Cache(config.get_cache_dir(), tag_index=True)
    # Make sure that we remove any data that wasn't cleaned up correctly for
    # some reason.
    _clean_cache()
    # Cleanup the cache at program exit.
    atexit.register(_close_cache)
  return _cache


deque_tmpdirs: List[str] = []


def _clean_tmp_deque():
  for d in deque_tmpdirs:
    logging.debug('deleting dequeue tempdir: %s', d)
    shutil.rmtree(d, ignore_errors=True)


def get_tmp_deque(prefix='tmp-deque-') -> diskcache.Deque:
  """Get a Diskcache.Deque object useful to temporarily store data (like logs).

  arguments:
    prefix: prefix to be added to the temporary directory (default: tmp-deque)
  """
  tempdir = tempfile.mkdtemp(prefix=prefix, dir=config.get_cache_dir())
  if not deque_tmpdirs:
    atexit.register(_clean_tmp_deque)
  deque_tmpdirs.append(tempdir)
  deque = diskcache.Deque(directory=tempdir)
  return deque


# Write our own implementation instead of using private function
# functtools._make_key, so that there is no breakage if that
# private function changes with a newer Python version.
def _make_key(func, args, kwargs):
  h = hashlib.sha256()
  func_name = bytes(func.__module__ + '.' + func.__name__ + ':', 'utf-8')
  h.update(pickle.dumps((args, kwargs)))
  # we don't hash the function name so that it's easier to debug
  key = func_name + h.digest()
  return key


@contextlib.contextmanager
def _acquire_timeout(lock, timeout, name):
  thread = threading.current_thread()
  orig_thread_name = thread.name
  thread.name = orig_thread_name + f'(waiting:{name})'
  result = lock.acquire(timeout=timeout)
  if not result:
    raise RuntimeError(f"Couldn't acquire lock for {name}.")
  try:
    thread.name = orig_thread_name + f'(lock:{name})'
    yield
  finally:
    thread.name = orig_thread_name
    if result:
      lock.release()


def cached_api_call(expire=None, in_memory=False):
  """Caching decorator optimized for API calls.

  This is very similar to functools.lru_cache, with the following differences:
  - uses diskcache so that the memory footprint doesn't grow uncontrollably (the
    API results might be big).
  - uses a lock so that if the function is called from two threads
    simultaneously, only one API call will be done and the other will wait until
    the result is available in the cache.

  Parameters:
  - expire: number of seconds until the key expires (default: expire when the
    process ends)
  - in_memory: if true the result will be kept in memory, similarly to
    lru_cache (but with the locking).
  """

  def _cached_api_call_decorator(func):
    lockdict = collections.defaultdict(threading.Lock)
    if in_memory:
      lru_cached_func = functools.lru_cache()(func)

    @functools.wraps(func)
    def _cached_api_call_wrapper(*args, **kwargs):
      key = None
      if _use_cache:
        logging.debug('looking up cache for %s', func.__name__)
        key = _make_key(func, args, kwargs)
        lock = lockdict[key]
        with _acquire_timeout(lock, config.CACHE_LOCK_TIMEOUT, func.__name__):
          if in_memory:
            if _get_bypass_cache():
              logging.debug('bypassing cache for %s, fetching fresh data.',
                            func.__name__)
              lru_cached_func.cache_clear()
            return lru_cached_func(*args, **kwargs)
          else:
            api_cache = get_disk_cache()
            if _get_bypass_cache():
              logging.debug('bypassing cache for %s, fetching fresh data.',
                            func.__name__)
            else:
              # We use 'no data' to be able to cache calls that returned None.
              cached_result = api_cache.get(key, default='no data')
              if cached_result != 'no data':
                logging.debug('returning cached result for %s', func.__name__)
                if isinstance(cached_result, Exception):
                  raise cached_result
                return cached_result
      else:
        logging.debug('caching is disabled for %s', func.__name__)
      # Call the function
      logging.debug('calling function %s (expire=%s, key=%s)', func.__name__,
                    str(expire), str(key))
      result = None
      try:
        result = func(*args, **kwargs)
        logging.debug('DONE calling function %s (expire=%s, key=%s)',
                      func.__name__, str(expire), str(key))
      except googleapiclient.errors.HttpError as err:
        # cache API errors as well
        result = err
      if _use_cache:
        if expire:
          api_cache.set(key, result, expire=expire)
        else:
          api_cache.set(key, result, tag='tmp')
      if isinstance(result, Exception):
        raise result
      return result

    return _cached_api_call_wrapper

  # Decorator without parens -> called with function as first parameter
  if callable(expire):
    func = expire
    expire = None
    return _cached_api_call_decorator(func)
  else:
    return _cached_api_call_decorator
