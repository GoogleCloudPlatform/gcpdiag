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

from gcp_doctor import config

_cache = None


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


def get_cache() -> diskcache.Cache:
  """Get a Diskcache.Cache object that can be used to cache data."""
  global _cache
  if not _cache:
    _cache = diskcache.Cache(config.CACHE_DIR, tag_index=True)
    # Make sure that we remove any data that wasn't cleaned up correctly for
    # some reason.
    _clean_cache()
    # Cleanup the cache at program exit.
    atexit.register(_close_cache)
  return _cache


deque_tmpdirs: List[str] = []


def _clean_tmp_deque():
  global deque_tmpdirs
  for d in deque_tmpdirs:
    logging.debug('deleting dequeue tempdir: %s', d)
    shutil.rmtree(d, ignore_errors=True)


def get_tmp_deque(prefix='tmp-deque-') -> diskcache.Deque:
  """Get a Diskcache.Deque object useful to temporily store data (like logs).

  arguments:
    prefix: prefix to be added to the temporary directory (default: tmp-deque)
  """
  tempdir = tempfile.mkdtemp(prefix=prefix, dir=config.CACHE_DIR)
  global deque_tmpdirs
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
  h.update(pickle.dumps(args))
  h.update(pickle.dumps(kwargs))
  # we don't hash the function name so that it's easier to debug
  key = func_name + h.digest()
  return key


@contextlib.contextmanager
def _acquire_timeout(lock, timeout):
  result = lock.acquire(timeout=timeout)
  if not result:
    raise RuntimeError('Couldn\'t aquire lock. API call taking too long?')
  yield
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
      key = _make_key(func, args, kwargs)
      lock = lockdict[key]
      with _acquire_timeout(lock, config.CACHE_LOCK_TIMEOUT):
        if in_memory:
          return lru_cached_func(*args, **kwargs)
        else:
          api_cache = get_cache()
          # We use 'no data' to be able to cache calls that returned None.
          cached_result = api_cache.get(key, default='no data')
          if cached_result != 'no data':
            logging.debug('returning cached result for %s', func.__name__)
            return cached_result
          logging.debug('calling function %s (expire=%s, key=%s)',
                        func.__name__, expire, key)
          result = func(*args, **kwargs)
          if expire:
            api_cache.set(key, result, expire=expire)
          else:
            api_cache.set(key, result, tag='tmp')
          return result

    return _cached_api_call_wrapper

  # Decorator without parens -> called with function as first parameter
  if callable(expire):
    func = expire
    expire = None
    return _cached_api_call_decorator(func)
  else:
    return _cached_api_call_decorator
