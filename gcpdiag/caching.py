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
"""Persistent caching using SQLite3."""

import atexit
import contextlib
import functools
import hashlib
import logging
import pathlib
import pickle
import shutil
import sqlite3
import tempfile
import threading
import time
import weakref
from typing import List, Optional

import googleapiclient.errors
import googleapiclient.http

from gcpdiag import config

_cache: Optional['SQLiteCache'] = None
_bypass_cache = False
_use_cache = True


class SQLiteCache:
  """A thread-safe, process-safe persistent Cache backed by SQLite3.

  This is a replacement for diskcache that is built into the google3 python
  standard library.
  This implementation lacks a size limit or an LRU eviction policy. The cache
  file will grow unbounded unless entries expire on their own or are explicitly
  evicted.
  """

  def __init__(self, directory: str, tag_index: bool = True):
    del tag_index  # Unused
    path = pathlib.Path(directory)
    # Restrict cache directory permissions to owner to mitigate pickle insecurity.
    path.mkdir(mode=0o700, parents=True, exist_ok=True)
    path.chmod(0o700)
    self.db_path = path / 'sqlite_cache.db'
    self._init_db()

  def _init_db(self):
    """Initializes the SQLite database and creates the cache table and indexes."""
    with contextlib.closing(sqlite3.connect(self.db_path, timeout=30.0)) as conn:
      with conn:
        conn.execute('PRAGMA journal_mode=WAL;')
        conn.execute("""
            CREATE TABLE IF NOT EXISTS cache (
                key BLOB PRIMARY KEY,
                value BLOB,
                expire REAL,
                tag TEXT
            );
        """)
        conn.execute('CREATE INDEX IF NOT EXISTS idx_tag ON cache(tag);')
        conn.execute('CREATE INDEX IF NOT EXISTS idx_expire ON cache(expire);')

  def get(self, key: bytes, default=None):
    """Retrieves a value from the cache.

    Args:
      key: The cache key (bytes).
      default: The value to return if the key is not found or has expired.

    Returns:
      The cached value if found and not expired, otherwise the default value.
    """
    now = time.time()
    try:
      with contextlib.closing(sqlite3.connect(self.db_path, timeout=30.0)) as conn:
        with conn:
          cur = conn.cursor()
          cur.execute('SELECT value, expire FROM cache WHERE key = ?', (sqlite3.Binary(key),))
          row = cur.fetchone()
          if row:
            value_bytes, expire = row
            if expire is not None and expire < now:
              return default
            return pickle.loads(value_bytes)
          return default
    except (sqlite3.Error, Exception) as e:
      logging.error('SQLiteCache.get error: %s', e)
      return default

  def set(self, key: bytes, value, expire=None, tag=None):
    """Stores a value in the cache.

    Args:
      key: The cache key (bytes).
      value: The value to cache.
      expire: Optional. The number of seconds from now when the cache entry
        should expire. If None, the entry will persist until explicitly evicted.
      tag: Optional. A string tag to group cache entries for eviction.
    """
    now = time.time()
    expire_time = (now + expire) if expire is not None else None
    value_bytes = pickle.dumps(value)
    try:
      with contextlib.closing(sqlite3.connect(self.db_path, timeout=30.0)) as conn:
        with conn:
          conn.execute(
            """
              INSERT OR REPLACE INTO cache (key, value, expire, tag)
              VALUES (?, ?, ?, ?)
              """,
            (sqlite3.Binary(key), sqlite3.Binary(value_bytes), expire_time, tag),
          )
    except sqlite3.Error as e:
      logging.error('SQLiteCache.set error: %s', e)

  def evict(self, tag: str) -> int:
    """Evicts all cache entries associated with a given tag.

    Args:
      tag: The tag used to group cache entries.

    Returns:
      The number of entries removed from the cache.
    """
    try:
      with contextlib.closing(sqlite3.connect(self.db_path, timeout=30.0)) as conn:
        with conn:
          cur = conn.cursor()
          cur.execute('DELETE FROM cache WHERE tag = ?', (tag,))
          return cur.rowcount
    except sqlite3.Error as e:
      logging.error('SQLiteCache.evict error: %s', e)
      return 0

  def expire(self) -> int:
    """Removes all expired cache entries.

    Returns:
      The number of expired entries removed from the cache.
    """
    now = time.time()
    try:
      with contextlib.closing(sqlite3.connect(self.db_path, timeout=30.0)) as conn:
        with conn:
          cur = conn.cursor()
          cur.execute('DELETE FROM cache WHERE expire < ?', (now,))
          return cur.rowcount
    except sqlite3.Error as e:
      logging.error('SQLiteCache.expire error: %s', e)
      return 0

  def close(self):
    """Closes the cache. Currently, this is a no-op."""
    pass


class SQLiteDeque:
  """A thread-safe, disk-backed sequence/deque backed by SQLite3."""

  def __init__(self, directory: str):
    path = pathlib.Path(directory)
    # Restrict cache directory permissions to owner to mitigate pickle insecurity.
    path.mkdir(mode=0o700, parents=True, exist_ok=True)
    path.chmod(0o700)
    self.db_path = path / 'sqlite_deque.db'
    self._init_db()

  def _init_db(self):
    with contextlib.closing(sqlite3.connect(self.db_path, timeout=30.0)) as conn:
      with conn:
        conn.execute('PRAGMA journal_mode=WAL;')
        conn.execute("""
            CREATE TABLE IF NOT EXISTS deque (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                value BLOB
            );
        """)

  def appendleft(self, value):
    value_bytes = pickle.dumps(value)
    with contextlib.closing(sqlite3.connect(self.db_path, timeout=30.0)) as conn:
      with conn:
        conn.execute('INSERT INTO deque (value) VALUES (?)', (sqlite3.Binary(value_bytes),))

  def __len__(self) -> int:
    with contextlib.closing(sqlite3.connect(self.db_path, timeout=30.0)) as conn:
      with conn:
        cur = conn.cursor()
        cur.execute('SELECT COUNT(*) FROM deque')
        return cur.fetchone()[0]

  def __iter__(self):
    with contextlib.closing(sqlite3.connect(self.db_path, timeout=30.0)) as conn:
      with conn:
        cur = conn.cursor()
        cur.execute('SELECT value FROM deque ORDER BY id DESC')
        rows = cur.fetchall()
    for row in rows:
      yield pickle.loads(row[0])

  def __reversed__(self):
    with contextlib.closing(sqlite3.connect(self.db_path, timeout=30.0)) as conn:
      with conn:
        cur = conn.cursor()
        cur.execute('SELECT value FROM deque ORDER BY id ASC')
        rows = cur.fetchall()
    for row in rows:
      yield pickle.loads(row[0])

  def __getitem__(self, index):
    if isinstance(index, int):
      if index < 0:
        length = len(self)
        index = length + index
        if index < 0:
          raise IndexError('deque index out of range')

      with contextlib.closing(sqlite3.connect(self.db_path, timeout=30.0)) as conn:
        with conn:
          cur = conn.cursor()
          cur.execute('SELECT value FROM deque ORDER BY id DESC LIMIT 1 OFFSET ?', (index,))
          row = cur.fetchone()
          if row is None:
            raise IndexError('deque index out of range')
          return pickle.loads(row[0])
    else:
      with contextlib.closing(sqlite3.connect(self.db_path, timeout=30.0)) as conn:
        with conn:
          cur = conn.cursor()
          cur.execute('SELECT value FROM deque ORDER BY id DESC')
          rows = cur.fetchall()
      values = [pickle.loads(row[0]) for row in rows]
      try:
        return values[index]
      except IndexError as e:
        raise IndexError('deque index out of range') from e


class RefLock:
  """Wrapper for threading.Lock to support weak referencing in LockDict."""

  def __init__(self):
    self.lock = threading.Lock()

  def acquire(self, *args, **kwargs):
    return self.lock.acquire(*args, **kwargs)

  def release(self):
    self.lock.release()

  def __enter__(self):
    return self.lock.__enter__()

  def __exit__(self, exc_type, exc_val, exc_tb):
    return self.lock.__exit__(exc_type, exc_val, exc_tb)


class LockDict:
  """Thread-safe dict of thread locks for cache synchronization.

  Uses weak references (WeakValueDictionary) to store locks, ensuring that
  lock objects are garbage-collected when no longer in use. This prevents
  the dictionary from growing unboundedly if cached functions are called
  with many different keys over time.
  """

  def __init__(self):
    self._locks = weakref.WeakValueDictionary()
    self._dict_lock = threading.Lock()

  def __getitem__(self, key):
    with self._dict_lock:
      lock = self._locks.get(key)
      if lock is None:
        lock = RefLock()
        self._locks[key] = lock
      return lock

  def __len__(self) -> int:
    with self._dict_lock:
      return len(self._locks)


def _set_bypass_cache(value: bool):
  """Sets the cache bypass flag for the current thread.
  Only set this for code that need to re-fetch fresh data
  regardless of expiry and state of cached data.
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
  """Used to enable or disable the use of caching in the application."""
  global _use_cache
  _use_cache = enabled


@contextlib.contextmanager
def bypass_cache():
  """A thread-safe context manager to temporarily set the cache bypass to True
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


def get_disk_cache() -> Optional[SQLiteCache]:
  """Get a SQLiteCache object that can be used to cache data."""
  global _cache
  if _use_cache and not _cache:
    _cache = SQLiteCache(config.get_cache_dir(), tag_index=True)
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


def get_tmp_deque(prefix='tmp-deque-') -> SQLiteDeque:
  """Get a SQLiteDeque object useful to temporarily store data (like logs).

  arguments:
    prefix: prefix to be added to the temporary directory (default: tmp-deque)
  """
  tempdir = tempfile.mkdtemp(prefix=prefix, dir=config.get_cache_dir())
  if not deque_tmpdirs:
    atexit.register(_clean_tmp_deque)
  deque_tmpdirs.append(tempdir)
  deque = SQLiteDeque(directory=tempdir)
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
  - uses SQLite persistent cache so that the memory footprint doesn't grow
    uncontrollably (the API results might be big).
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
    lockdict = LockDict()
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
              logging.debug('bypassing cache for %s, fetching fresh data.', func.__name__)
              lru_cached_func.cache_clear()
            return lru_cached_func(*args, **kwargs)
          else:
            api_cache = get_disk_cache()
            if _get_bypass_cache():
              logging.debug('bypassing cache for %s, fetching fresh data.', func.__name__)
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
      logging.debug('calling function %s (expire=%s, key=%s)', func.__name__, str(expire), str(key))
      result = None
      try:
        result = func(*args, **kwargs)
        logging.debug(
          'DONE calling function %s (expire=%s, key=%s)', func.__name__, str(expire), str(key)
        )
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
