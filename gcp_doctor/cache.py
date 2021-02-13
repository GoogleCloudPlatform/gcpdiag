# Lint as: python3
"""Persistent caching using diskcache."""

import diskcache

from gcp_doctor import config

_cache = None


def get_cache() -> diskcache.Cache:
  global _cache
  if not _cache:
    _cache = diskcache.Cache(config.CACHE_DIR, shards=4)
  return _cache
